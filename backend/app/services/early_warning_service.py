"""
Early Warning Service - Phase 6 Checkpoint 15.2 & Phase 7 Checkpoint 16.5

Translates environmental hazard indices and satellite change indicators
into structured operational warning levels (NORMAL, WATCH, ALERT, CRITICAL).
Provides decision-support recommendations while maintaining strict separation of
environmental hazard models from independent ground observation field intelligence.
"""

from typing import Dict, Any, Optional

class EarlyWarningService:
    @staticmethod
    def evaluate_warning_status(
        composite_hazard_data: Dict[str, Any],
        radar_change_data: Optional[Dict[str, Any]] = None,
        iot_payload: Optional[Dict[str, Any]] = None,
        field_intelligence_signal: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Processes hazard, satellite, and field intelligence inputs to determine operational warning levels.
        Maintains independent ground observation context without altering the environmental risk category.
        """
        # 1. Parse Composite Hazard data
        hazard_score = float(composite_hazard_data.get("composite_risk_index", 0.0))
        hazard_level = composite_hazard_data.get("risk_level", "Unknown")
        components = composite_hazard_data.get("components", {})
        
        rainfall_score = 0.0
        if "rainfall_trigger" in components:
            rainfall_score = float(components["rainfall_trigger"].get("rainfall_score", 0.0))

        # 2. Parse Satellite Surface Change data
        is_sat_available = False
        rsci_score = 0.0
        rsci_category = "N/A"
        
        if radar_change_data and radar_change_data.get("status") == "PAIRED_SUCCESS":
            signal = radar_change_data.get("radar_surface_change_signal", {})
            if signal:
                is_sat_available = True
                rsci_score = float(signal.get("radar_surface_change_index", 0.0))
                rsci_category = signal.get("category", "Stable")

        # 3. Determine Operational Mode and Satellite Availability Status
        operational_mode = "FULL_EVIDENCE" if is_sat_available else "METEOROLOGICAL_FALLBACK"
        satellite_availability = (
            f"Available - Active pair comparison (RSCI: {rsci_score:.1f}, Category: {rsci_category})"
            if is_sat_available else "Unavailable - Missing or incompatible scene alignment"
        )

        # 4. Core Environmental Warning Level Logic (Green -> Yellow -> Orange -> Red)
        warning_level = "NORMAL"
        reasoning = ""
        
        if is_sat_available:
            # Full Evidence Mode logic
            if hazard_score > 75.0 and rsci_score > 75.0:
                warning_level = "CRITICAL"
                reasoning = (
                    f"Slope exhibits very high susceptibility under active meteorological triggers "
                    f"(Hazard Index: {hazard_score:.1f}) combined with significant radar-observed "
                    f"surface change (RSCI: {rsci_score:.1f}). Imminent slope failure is possible."
                )
            elif (hazard_score > 75.0 and rsci_score > 25.0) or \
                 (50.0 < hazard_score <= 75.0 and rsci_score > 50.0):
                warning_level = "ALERT"
                reasoning = (
                    f"Active meteorological triggers on susceptible slopes (Hazard Index: {hazard_score:.1f}) "
                    f"coincide with moderate-to-significant surface backscatter alterations "
                    f"(RSCI: {rsci_score:.1f}). Heightened preparedness is advised."
                )
            elif hazard_score > 50.0 or rsci_score > 50.0:
                warning_level = "WATCH"
                reasoning = (
                    f"Elevated signals detected: either active weather trigger on susceptible terrain "
                    f"(Hazard Index: {hazard_score:.1f}) OR unexplained ground backscatter changes "
                    f"(RSCI: {rsci_score:.1f}). Visual and sensor monitoring is recommended."
                )
            else:
                warning_level = "NORMAL"
                reasoning = (
                    f"Low composite hazard triggers (Hazard Index: {hazard_score:.1f}) and "
                    f"stable satellite surface return (RSCI: {rsci_score:.1f}). Standard baseline conditions."
                )
        else:
            # Meteorological Fallback Mode logic
            if hazard_score > 75.0 and rainfall_score > 20.0:
                warning_level = "CRITICAL"
                reasoning = (
                    f"Extreme cumulative precipitation trigger (Rainfall Score: {rainfall_score:.1f}) acting on "
                    f"highly vulnerable terrain (Hazard Index: {hazard_score:.1f}). Operational review "
                    f"should be initiated under meteorological fallback protocols."
                )
            elif (hazard_score > 75.0 and 15.0 < rainfall_score <= 20.0) or \
                 (50.0 < hazard_score <= 75.0 and rainfall_score > 15.0):
                warning_level = "ALERT"
                reasoning = (
                    f"Meaningful rainfall trigger evidence (Rainfall Score: {rainfall_score:.1f}) on susceptible slopes "
                    f"(Hazard Index: {hazard_score:.1f}). Observational verification is unavailable."
                )
            elif hazard_score > 50.0:
                # High hazard + low rainfall -> WATCH
                if hazard_score > 75.0:
                    reasoning = (
                        f"Highly susceptible slope (Hazard Index: {hazard_score:.1f}) under low/minor rainfall trigger "
                        f"conditions (Rainfall Score: {rainfall_score:.1f}). Warning level remains WATCH "
                        f"due to lack of active dynamic precipitation triggers."
                    )
                else:
                    reasoning = (
                        f"Susceptible slope (Hazard Index: {hazard_score:.1f}) under low/minor rainfall trigger "
                        f"conditions (Rainfall Score: {rainfall_score:.1f}). Meteorological monitoring is flagged at WATCH."
                    )
                warning_level = "WATCH"
            else:
                warning_level = "NORMAL"
                reasoning = f"Low environmental hazard triggers (Hazard Index: {hazard_score:.1f}) and stable rainfall conditions."

        # 5. Map warning level to recommended actions
        actions = {
            "NORMAL": "Continue routine monitoring. Check system telemetry daily.",
            "WATCH": "Increase observation frequency. Verify local rainfall telemetry and check for recent surface reports.",
            "ALERT": "Alert local disaster management authorities. Prepare emergency shelters, initiate visual patrols, and notify local communities to stand by.",
            "CRITICAL": "Initiate urgent protective action and emergency authority review according to local disaster-management protocols."
        }
        
        scientific_notice = (
            "Early Warning Decision Engine output represents an operational decision-support recommendation "
            "based on environmental triggers and relative satellite observations. It does not predict with "
            "certainty, imply imminent structural failure, or confirm landslide occurrences."
        )

        # 6. Parse Ground Observation Context (Independent observational intelligence layer)
        ground_observation_context = None
        if field_intelligence_signal:
            status_val = field_intelligence_signal.get("field_intelligence_status") or field_intelligence_signal.get("status", "NORMAL")
            if hasattr(status_val, "value"):
                status_val = status_val.value

            verified_score = 0.0
            if "verified_ground_signal" in field_intelligence_signal and isinstance(field_intelligence_signal["verified_ground_signal"], dict):
                verified_score = float(field_intelligence_signal["verified_ground_signal"].get("score", 0.0))
            elif "verified_ground_signal_score" in field_intelligence_signal:
                verified_score = float(field_intelligence_signal["verified_ground_signal_score"])

            msg = field_intelligence_signal.get("operational_message", "")
            ground_observation_context = {
                "status": status_val,
                "message": msg,
                "verified_signal_score": verified_score
            }
        elif composite_hazard_data.get("field_intelligence_context"):
            fic = composite_hazard_data["field_intelligence_context"]
            ground_observation_context = {
                "status": fic.get("status", "NORMAL"),
                "message": fic.get("operational_message", ""),
                "verified_signal_score": float(fic.get("verified_ground_signal_score", 0.0))
            }

        return {
            "warning_level": warning_level,
            "operational_mode": operational_mode,
            "hazard_context": {
                "composite_hazard_index": hazard_score,
                "categorical_hazard_level": hazard_level,
                "rainfall_trigger_score": rainfall_score
            },
            "evidence_summary": {
                "satellite_available": is_sat_available,
                "rsci_score": rsci_score if is_sat_available else None,
                "rsci_category": rsci_category
            },
            "recommended_action": actions.get(warning_level, "Monitor routine updates."),
            "reasoning": reasoning,
            "satellite_availability": satellite_availability,
            "scientific_notice": scientific_notice,
            "ground_observation_context": ground_observation_context
        }
