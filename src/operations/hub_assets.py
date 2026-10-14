"""Permanent Hub assets use direct transfers, never temporary package receipts."""
from src.execution.commands import Command, CommandType
from src.planner.task import Task

ASSETS = {'manny', 'additional_container'}


def advance_assets(service, delivery, excluded_container_ids, decision):
    from src.operations.infrastructure import stock, point, inventory_items
    from src.operations.hub_receiving import empty_container
    ops = service.operations
    requested = delivery['items']
    baseline = delivery['assetBaseline']
    shipment = delivery.get('assetShipment')
    inventory = inventory_items(ops)
    attached = {str(c['id']): c for c in ops.containers.attached()}
    if shipment:
        present = (shipment['id'] in attached if shipment['kind'] == 'additional_container' else
                   any(str(i.get('id')) == shipment['id'] for i in inventory)
                   or any(str(m.get('id')) == shipment['id'] for m in ops.world.mannies.get('mannies', [])))
        accepted = ops.data_engine.action_was_successful(shipment['fingerprint'])
        if not present and accepted:
            # A permanent delivery changes count/capacity without a receipt
            # gate. Require fresh receiver telemetry before another handoff.
            if hasattr(ops.data_engine, 'set_preference'):
                ops.data_engine.set_preference(f"hub_receiving:{delivery['targetProbeId']}", '{}')
            kind = shipment['kind']
            requested[kind] -= 1
            if not requested[kind]:
                requested.pop(kind)
            delivery.pop('assetShipment')
            delivery['assetSequence'] = delivery.get('assetSequence', 0) + 1
            return decision('asset_delivered', 'Permanent asset transfer confirmed; continuing this package.')
        if not present or accepted:
            return decision('asset_sync', 'Waiting for authoritative asset-transfer confirmation.')
    available = stock(ops)
    kind = next((k for k in ('additional_container', 'manny') if requested.get(k)), None)
    if kind is None:
        return None
    if available.get(kind, 0) <= baseline.get(kind, 0):
        return decision('producing', 'Crafting additional assets for this package while retaining the Hub stock.')
    ready, blocker, summary = service.receiver_state(delivery['targetProbeId'])
    if blocker:
        return decision(blocker, summary)
    if kind == 'additional_container':
        if ready.get('containerCount', 0) >= ready.get('safeLimit', 0):
            return decision('receiver_storage_limit', 'Permanent container delivery would exceed the receiver travel-safe limit.')
        candidates = [key for key in attached if key not in excluded_container_ids
                      and key != delivery.get('containerId') and empty_container(ops, key)]
        identifier = shipment['id'] if shipment else next(iter(candidates), None)
        if identifier not in candidates:
            return decision('asset_wait', 'Waiting for an empty unreserved permanent container.')
        action, command_type = 'Deliver Hub Container', CommandType.MANNY_DETACH_STORAGE_CONTAINER
        payload = {'containerId':identifier, 'mode':'attach_to_probe', 'objectId':str(delivery['targetProbeId'])}
        metadata = {'mode':'attach_to_probe', 'objectId':str(delivery['targetProbeId'])}
    else:
        pending_boxes = {delivery.get('containerId'), *excluded_container_ids}
        from src.operations.hub_receiving import receipts
        pending_boxes.update(op.metadata['containerId'] for op in receipts(ops.data_engine, ops.world.probe['id']))
        candidates = []
        for manny in ops.mining.idle_mannies():
            item = next((i for i in inventory if str(i.get('id')) == str(manny['id'])), {})
            if any(float(manny.get('cargo', {}).get(k, 0) or 0) > 0 for k in ('deuterium','metals','ice','organicCompounds','carbon_compounds')):
                continue
            size = item.get('containerSpace')
            if (size is not None and str((item.get('container') or {}).get('id')) not in pending_boxes
                    and any(float(free) >= float(size) for free in ready.get('storageFreeCapacities', []))):
                candidates.append(str(manny['id']))
        identifier = shipment['id'] if shipment else next(iter(candidates), None)
        if identifier not in candidates:
            return decision('asset_wait', 'Waiting for an idle transferable Manny and permanent receiver storage.')
        action, command_type = 'Transfer Hub Manny', CommandType.MANNY_TRANSFER_PROBE
        payload = {'targetProbeId':int(delivery['targetProbeId'])}
        metadata = {'targetProbeId':int(delivery['targetProbeId'])}
    metadata.update(hubCampaign=True, hubAsset=True, requestId=delivery['id'],
                    expectedSector=point(ops.travel.current_sector()))
    scope = f"hub:{delivery['id']}:asset:{delivery.get('assetSequence',0)}:{identifier}"
    reason = 'Transfer the requested permanent asset to the receiver.'
    task = Task(action=action, target=identifier, category='infrastructure', priority=1,
                reason=reason, workflow_authorized=True, idempotency_scope=scope, metadata=metadata)
    command = Command(command_type, ops.world.probe['id'], payload, reason, 1,
                      target_id=identifier if kind == 'manny' else None,
                      metadata={**metadata, 'workflowAuthorized':True, 'idempotencyScope':scope})
    delivery['assetShipment'] = {'kind':kind, 'id':identifier, 'fingerprint':command.fingerprint}
    return decision('delivering_asset', reason, tasks=(task,))
