"""Behavioral coverage for user-selected, protected upgrade campaigns."""
from dataclasses import replace
from types import SimpleNamespace

from src.data import DataEngine
from src.execution import (CommandPreparer, ExecutionMode, ExecutionPolicy,
                           CapabilityDispatcher, AutomationRuntime, PreparedCommand)
from src.execution.commands import Command, CommandType
from src.execution.preflight import PreflightValidator
from src.operations.upgrades import UpgradeService, installation_command
from src.planner.desired_state import DesiredState, UpgradeGoal, ProductionGoal
from src.planner.desired_state_store import DesiredStateStore
from src.planner.planner import Planner
from tests.test_planner_missions import build_operations


def scenario(tmp_path, *, metals=0, ingredients=None):
    operations = build_operations(metals=metals)
    operations.data_engine = DataEngine(tmp_path / 'upgrade.sqlite3')
    operations.world.hazard_context = {'improvements': {'improvements': [{
        'id': 'compression', 'name': 'Compression', 'available': True,
        'done': False, 'installableOnProbe': True,
        'ingredients': ingredients if ingredients is not None else [
            {'type': 'storage_container', 'kind': 'item', 'quantity': 2},
            {'type': 'metals', 'kind': 'resource', 'quantity': 0.5},
        ],
    }]}}
    desired = replace(DesiredState.unconfigured(), upgrade=UpgradeGoal('compression', 'test-campaign'))
    DesiredStateStore(operations.data_engine).save(desired, 1)
    return operations, desired


def prepare(operations, desired, mode=ExecutionMode.AUTOMATIC):
    policy = ExecutionPolicy(mode=mode, live_execution_enabled=True, max_commands_per_cycle=20)
    return CommandPreparer(operations, 1, policy).prepare(Planner(operations, desired).tasks())


def store_items(operations, count):
    operations.world.probe['inventory']['items'] = [
        {'id': 'stack', 'type': 'storage_container', 'quantity': count}]


def test_mines_then_crafts_then_installs_exact_live_requirements(tmp_path):
    operations, desired = scenario(tmp_path)
    prepared = prepare(operations, desired)
    mine = next(row.command for row in prepared if row.command.type == CommandType.MANNY_MINE)
    assert mine.metadata['requestedNeed'] == 1.5  # next craft + direct installation metals
    assert 'targetContainerId' not in mine.payload
    assert mine.metadata['workflowAuthorized']
    operations.world.probe['inventory']['resourceStocks'][0]['amount'] = 1.5
    craft = next(row for row in prepare(operations, desired) if row.command.type == CommandType.MANNY_CRAFT)
    assert craft.disposition == 'ready'
    assert craft.command.payload == {'recipe': 'storage_container'}
    store_items(operations, 2)
    operations.world.probe['inventory']['resourceStocks'][0]['amount'] = 0.5
    install = next(row for row in prepare(operations, desired) if row.command.type == CommandType.MANNY_UPGRADE)
    assert install.disposition == 'ready'
    calls = []
    CapabilityDispatcher(SimpleNamespace(mannies=SimpleNamespace(
        start_task=lambda *args: calls.append(args)))).dispatch(install.command)
    assert calls == [(1, 101, 'improve-probe', {'improvement': 'compression'})]


def test_active_outputs_prevent_duplicate_crafts_but_cannot_start_installation(tmp_path):
    operations, desired = scenario(tmp_path, metals=1)
    store_items(operations, 1)
    operations.world.mannies['mannies'].append({'id': 102, 'currentTask': 'crafting',
        'task': {'recipe': 'storage_container'}, 'canReceiveOrders': False})
    tasks = Planner(operations, desired).tasks()
    assert not any(task.action in {'Craft Item', 'Install Probe Upgrade'} for task in tasks)
    assert UpgradeService(operations).assess(desired.upgrade)['status'] == 'preparing'


def test_protected_components_block_other_crafts_even_at_higher_priority(tmp_path):
    operations, desired = scenario(tmp_path, metals=10)
    desired = replace(desired, upgrade=replace(desired.upgrade, priority=5))
    DesiredStateStore(operations.data_engine).save(desired, 1)
    store_items(operations, 1)
    operations.manufacturing.recipes._recipes['consumer'] = {
        'id': 'consumer', 'craftableBy': ['manny'], 'durationSeconds': 1,
        'ingredients': [{'kind': 'item', 'type': 'storage_container', 'quantity': 1}],
        'output': {'type': 'consumer', 'containerSpace': 0.1}}
    desired = replace(desired, production=(ProductionGoal('consumer', 1, priority=1),))
    blocked = next(row for row in prepare(operations, desired) if row.command.payload.get('recipe') == 'consumer')
    assert 'item_reserved_by_upgrade' in blocked.blockers
    # Surplus remains usable.
    store_items(operations, 3)
    assert not UpgradeService(operations).command_blockers(blocked.command, desired.upgrade)


def test_direct_raw_inputs_are_saved_while_mining_for_components(tmp_path):
    operations, desired = scenario(tmp_path, metals=0.5)
    tasks = Planner(operations, desired).tasks()
    assert not any(task.action == 'Craft Item' for task in tasks)
    command = Command(CommandType.MANNY_CRAFT, 1, {'recipe': 'storage_container'}, 'other', 1, 101)
    assert 'resource_reserved_by_upgrade' in PreflightValidator(operations, 1).blockers(command)


def test_upgrade_goal_is_durable_and_probe_scoped_and_cancellation_releases_claims(tmp_path):
    operations, desired = scenario(tmp_path, metals=1)
    store_items(operations, 1)
    store = DesiredStateStore(operations.data_engine)
    assert store.load(1).upgrade == desired.upgrade
    assert store.load(2).upgrade is None
    command = Command(CommandType.MANNY_REPAIR, 1, {'integrityPercent': 100}, 'repair', 1, 101)
    assert 'resource_reserved_by_upgrade' in PreflightValidator(operations, 1).blockers(command)
    store.save(replace(desired, upgrade=None), 1)
    assert not PreflightValidator(operations, 1).blockers(command)
    assert 'upgrade_goal_changed' in PreflightValidator(operations, 1).blockers(installation_command(1, desired.upgrade, 101))


def test_live_preflight_rejects_changed_inputs_blueprints_and_busy_workers(tmp_path):
    operations, desired = scenario(tmp_path, metals=0.5)
    store_items(operations, 2)
    command = installation_command(1, desired.upgrade, 101)
    assert not PreflightValidator(operations, 1).blockers(command)
    store_items(operations, 1)
    assert 'upgrade_not_ready' in PreflightValidator(operations, 1).blockers(command)
    store_items(operations, 2)
    operations.world.mannies['mannies'][0]['currentTask'] = 'mining'
    assert 'manny_unavailable' in PreflightValidator(operations, 1).blockers(command)
    operations.world.hazard_context['improvements']['improvements'][0]['available'] = False
    assert 'upgrade_not_ready' in PreflightValidator(operations, 1).blockers(command)


def test_accepted_installation_never_rebuilds_or_duplicates_during_telemetry_lag(tmp_path):
    operations, desired = scenario(tmp_path, metals=0.5)
    store_items(operations, 2)
    command = installation_command(1, desired.upgrade, 101)
    calls = []
    runtime = AutomationRuntime(capabilities=None, data_engine=operations.data_engine,
        policy=ExecutionPolicy(mode=ExecutionMode.AUTOMATIC, live_execution_enabled=True),
        dispatcher=SimpleNamespace(dispatch=lambda cmd: calls.append(cmd) or {'accepted': True}),
        refresh=lambda probe_id: operations)
    assert runtime.execute(PreparedCommand(command, 'ready')).status == 'succeeded'
    other_worker = installation_command(1, desired.upgrade, 102)
    assert other_worker.fingerprint == command.fingerprint
    assert runtime.execute(PreparedCommand(other_worker, 'ready')).status == 'cancelled'
    store_items(operations, 0)
    assert not prepare(operations, desired)
    assert len(calls) == 1
    # A reconstructed service after restart still observes the durable receipt.
    assert UpgradeService(operations).assess(DesiredStateStore(operations.data_engine).load(1).upgrade)['status'] == 'installing'


def test_policy_modes_and_emergency_stop_still_apply(tmp_path):
    operations, desired = scenario(tmp_path, metals=0.5)
    store_items(operations, 2)
    for mode, disposition in [(ExecutionMode.OBSERVE, 'dry_run'), (ExecutionMode.APPROVE, 'awaiting_approval')]:
        row = next(row for row in prepare(operations, desired, mode) if row.command.type == CommandType.MANNY_UPGRADE)
        assert row.disposition == disposition
    operations.data_engine.set_emergency_stop(True)
    runtime = AutomationRuntime(capabilities=None, data_engine=operations.data_engine,
        policy=ExecutionPolicy(mode=ExecutionMode.AUTOMATIC, live_execution_enabled=True),
        dispatcher=SimpleNamespace(dispatch=lambda cmd: (_ for _ in ()).throw(AssertionError('dispatched'))),
        refresh=lambda probe_id: operations)
    assert runtime.execute(PreparedCommand(installation_command(1, desired.upgrade, 101), 'ready')).blockers == ('emergency_stop',)


def test_completed_and_non_probe_blueprints_never_generate_work(tmp_path):
    operations, desired = scenario(tmp_path)
    improvement = operations.world.hazard_context['improvements']['improvements'][0]
    improvement['installableOnProbe'] = False
    assert not prepare(operations, desired)
    improvement.update(installableOnProbe=True, done=True)
    assert not prepare(operations, desired)


def test_deuterium_shortage_uses_tank_units(tmp_path):
    operations, desired = scenario(tmp_path, ingredients=[{'kind': 'resource', 'type': 'deuterium', 'quantity': 1}])
    mine = next(row.command for row in prepare(operations, desired) if row.command.type == CommandType.MANNY_MINE)
    assert mine.metadata['requestedNeed'] == 50
    assert mine.payload['targetAmount'] <= 0.5


def test_upgrade_can_build_consumers_before_replacing_reserved_subcomponents(tmp_path):
    operations, desired = scenario(tmp_path, metals=10, ingredients=[
        {'kind': 'item', 'type': 'consumer', 'quantity': 1},
        {'kind': 'item', 'type': 'storage_container', 'quantity': 1},
    ])
    store_items(operations, 1)
    operations.manufacturing.recipes._recipes['consumer'] = {
        'id': 'consumer', 'craftableBy': ['manny'], 'durationSeconds': 1,
        'ingredients': [{'kind': 'item', 'type': 'storage_container', 'quantity': 1}],
        'output': {'type': 'consumer', 'containerSpace': 0.1}}
    first = next(row for row in prepare(operations, desired) if row.command.type == CommandType.MANNY_CRAFT)
    assert first.command.payload['recipe'] == 'consumer'
    assert first.disposition == 'ready'
    operations.world.probe['inventory']['items'] = [{'id': 'built', 'type': 'consumer'}]
    second = next(row for row in prepare(operations, desired) if row.command.type == CommandType.MANNY_CRAFT)
    assert second.command.payload['recipe'] == 'storage_container'
    assert second.disposition == 'ready'


def test_missing_catalog_cannot_silently_release_upgrade_stock(tmp_path):
    operations, desired = scenario(tmp_path, metals=10)
    operations.world.hazard_context = {}
    command = Command(CommandType.MANNY_CRAFT, 1, {'recipe': 'storage_container'}, 'other', 1, 101)
    assert 'upgrade_requirements_unavailable' in PreflightValidator(operations, 1).blockers(command)


def test_miner_reservations_yield_to_explicit_upgrade_and_resume_after_completion(tmp_path):
    from src.ui.controller import MissionControlDataService
    operations, desired = scenario(tmp_path)
    service = MissionControlDataService.__new__(MissionControlDataService)
    service.data_engine = operations.data_engine
    returned, tasks, view = service._reconcile_miner_campaign(operations, 1, desired)
    assert returned == desired
    assert not tasks
    assert view['paused'] and view['phase'] == 'upgrade'
    assert not view.get('reserveOrdinaryMannies', 0)


def test_small_real_resource_shortage_still_generates_mining(tmp_path):
    operations, desired = scenario(tmp_path, metals=0.4998, ingredients=[
        {'kind': 'resource', 'type': 'metals', 'quantity': 0.5}])
    mine = next(row.command for row in prepare(operations, desired) if row.command.type == CommandType.MANNY_MINE)
    assert mine.payload['targetAmount'] >= 0.001


def test_unidentified_active_upgrade_keeps_selected_goal_reservations(tmp_path):
    operations, desired = scenario(tmp_path, metals=1)
    operations.world.mannies['mannies'].append({
        'id': 102, 'currentTask': 'improving_probe', 'canReceiveOrders': False})
    view = UpgradeService(operations).assess(desired.upgrade)
    assert view['status'] == 'waiting'
    assert not prepare(operations, desired)
    other = Command(CommandType.MANNY_REPAIR, 1, {'integrityPercent': 100}, 'repair', 1, 101)
    assert 'resource_reserved_by_upgrade' in PreflightValidator(operations, 1).blockers(other)
