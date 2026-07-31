pragma Singleton
import QtQuick

QtObject {
    readonly property url iconRoot: Qt.resolvedUrl("../assets/icons/")

    function icon(name) {
        return iconRoot + name + ".png";
    }

    function probeIcon(model) {
        return icon(model === "deuterium_tanker" ? "probe-tanker" : "probe");
    }

    function relayStateBadge(status) {
        const state = ["active", "degraded", "offline"].includes(status) ? status : "offline";
        return icon("badge-relay-" + state);
    }

    function resourceBadge(resource) {
        const names = {
            "deuterium": "deuterium",
            "metals": "metals",
            "ice": "ice",
            "carbon_compounds": "carbon-compounds"
        };
        return icon("badge-resource-" + (names[resource] || "depleted"));
    }

    function compositionBadge(composition) {
        return icon("badge-composition-" + composition.replaceAll("_", "-"));
    }

    function objectIcon(type, properties) {
        const details = properties || {};
        if (type === "planet" && details.category)
            return icon("planet-" + details.category.replaceAll("_", "-"));
        if (type === "star" && details.remnant)
            return icon("star-remnant");

        const names = {
            "star": "star",
            "planet": "planet-rocky",
            "asteroid": details.resources ? "resource-asteroid" : "wandering-asteroid",
            "dust_cloud": "dust-cloud",
            "black_hole": "black-hole",
            "solar_system": "solar-system",
            "manny": "manny",
            "drifting_item": "drifting-item",
            "detached_container": "detached-container",
            "deuterium_refuel_station": "deuterium-station",
            "dormant_construct": "dormant-construct",
            "scut_relay": "scut-relay"
        };
        return icon(names[type] || "unknown-object");
    }
}
