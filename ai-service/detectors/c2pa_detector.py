import io
import json
from PIL import Image
from detectors.base import BaseDetector

try:
    import c2pa
    C2PA_AVAILABLE = True
except ImportError:
    C2PA_AVAILABLE = False

class C2PADetector(BaseDetector):
    """
    C2PA Content Credentials Detector.
    Verifies cryptographic signatures and checks for metadata indicating AI generation.
    """
    def _load_model(self) -> bool:
        return True

    def _detect_generator(self, manifest_data: dict) -> str:
        """Helper to identify the AI generator from the manifest details."""
        try:
            active_manifest_id = manifest_data.get("active_manifest")
            manifests = manifest_data.get("manifests", {})
            if not active_manifest_id or not manifests:
                return None

            active_manifest = manifests.get(active_manifest_id, {})
            claim_generator = str(active_manifest.get("claim_generator", "")).lower()

            # Collect candidate strings
            candidates = [claim_generator]
            
            # Extract softwareAgent and digitalSourceType from assertions
            assertions = active_manifest.get("assertions", [])
            for assertion in assertions:
                label = assertion.get("label", "")
                data = assertion.get("data", {})
                if "actions" in label:
                    actions_list = data.get("actions", [])
                    for action in actions_list:
                        agent = action.get("softwareAgent", {})
                        if isinstance(agent, dict):
                            candidates.append(str(agent.get("name", "")).lower())
                        elif isinstance(agent, str):
                            candidates.append(agent.lower())
                        
                        dst = str(action.get("digitalSourceType", "")).lower()
                        candidates.append(dst)
                if "digital-source-type" in label:
                    dst = str(data.get("digitalSourceType", "")).lower()
                    candidates.append(dst)

            # Dictionary mapping keywords to clean generator names
            keywords_map = {
                "openai": "OpenAI",
                "gpt": "OpenAI",
                "dall-e": "OpenAI",
                "dalle": "OpenAI",
                "imagen": "Google Imagen",
                "gemini": "Gemini",
                "firefly": "Adobe Firefly",
                "midjourney": "Midjourney",
                "stable diffusion": "Stable Diffusion",
                "stability": "Stable Diffusion",
                "sdxl": "Stable Diffusion",
                "flux": "Flux",
                "black forest": "Flux",
                "ideogram": "Ideogram",
                "leonardo": "Leonardo AI",
                "runway": "Runway",
                "recraft": "Recraft",
                "copilot": "Copilot"
            }

            for candidate in candidates:
                for kw, mapped in keywords_map.items():
                    if kw in candidate:
                        return mapped
        except Exception:
            pass
        return None

    def _predict(self, pil_image: Image.Image, **kwargs) -> dict:
        file_bytes = kwargs.get("file_bytes")
        mime_type = kwargs.get("mime_type", "image/jpeg")

        details = {
            "c2pa_detected": False,
            "c2pa_valid": False,
            "is_ai_generated": False,
            "generator": None,
            "claim_generator": None,
            "validation_status": None,
            "certificate_chain_valid": True,
            "has_edit_history": False,
            "has_provenance_chain": False,
            "manifest_count": 0,
            "tampering_indicators": [],
            "evidence_summary": []
        }

        if not C2PA_AVAILABLE:
            details["error"] = "c2pa-python package not installed or failed to load binary bindings."
            details["evidence_summary"] = ["No C2PA Content Credentials found"]
            return {
                "score": 0.0,
                "confidence": 0.0,
                "details": details
            }

        if not file_bytes:
            details["error"] = "Original file bytes were not provided to the detector."
            details["evidence_summary"] = ["No C2PA Content Credentials found"]
            return {
                "score": 0.0,
                "confidence": 0.0,
                "details": details
            }

        try:
            stream = io.BytesIO(file_bytes)
            with c2pa.Reader(mime_type, stream) as reader:
                manifest_json = reader.json()

                if manifest_json:
                    details["c2pa_detected"] = True
                    manifest_data = json.loads(manifest_json)
                    details["manifest_info"] = manifest_data

                    # Determine validation status
                    validation_state = None
                    try:
                        validation_state = reader.get_validation_status()
                    except AttributeError:
                        try:
                            validation_state = reader.get_validation_state()
                        except Exception:
                            pass

                    # Parse manifests
                    manifests = manifest_data.get("manifests", {})
                    details["manifest_count"] = len(manifests)
                    active_manifest_id = manifest_data.get("active_manifest")
                    active_manifest = manifests.get(active_manifest_id, {}) if active_manifest_id else {}

                    details["claim_generator"] = active_manifest.get("claim_generator")

                    # Provenance chain indicators
                    ingredients = active_manifest.get("ingredients", [])
                    details["has_provenance_chain"] = (details["manifest_count"] > 1) or (len(ingredients) > 0)

                    # Edit history indicator
                    has_edits = False
                    assertions = active_manifest.get("assertions", [])
                    for assertion in assertions:
                        if "actions" in assertion.get("label", ""):
                            actions_list = assertion.get("data", {}).get("actions", [])
                            if len(actions_list) > 0:
                                has_edits = True
                                break
                    details["has_edit_history"] = has_edits

                    # Generator detection
                    generator = self._detect_generator(manifest_data)
                    details["generator"] = generator

                    # Check digitalSourceType
                    is_ai = False
                    if generator is not None:
                        is_ai = True
                    else:
                        for assertion in assertions:
                            label = assertion.get("label", "")
                            data = assertion.get("data", {})
                            if "digital-source-type" in label:
                                dst = str(data.get("digitalSourceType", "")).lower()
                                if "trainedalgorithmicmedia" in dst or "synthetic" in dst:
                                    is_ai = True
                                    break
                            elif "actions" in label:
                                actions_list = data.get("actions", [])
                                for action in actions_list:
                                    dst = str(action.get("digitalSourceType", "")).lower()
                                    if "trainedalgorithmicmedia" in dst or "synthetic" in dst:
                                        is_ai = True
                                        break
                                if is_ai:
                                    break

                    details["is_ai_generated"] = is_ai

                    # Validation and Tampering checks
                    validation_errors = []
                    tampering_indicators = []
                    certificate_chain_valid = True

                    # 1. Parse validation_status list if present
                    validation_status_json = manifest_data.get("validation_status", [])
                    if isinstance(validation_status_json, list):
                        for status in validation_status_json:
                            code = status.get("code") or status.get("status") or ""
                            if code and code not in ["success", "claim.validated"]:
                                validation_errors.append(status)
                                if "signingcredential" in code.lower():
                                    certificate_chain_valid = False
                                if any(term in code.lower() for term in ["mismatch", "tampered", "missing", "invalid", "fail"]):
                                    tampering_indicators.append(f"Validation failure: {code} - {status.get('explanation', '')}")

                    # 2. Parse validation_results if present
                    validation_results = manifest_data.get("validation_results", {})
                    if isinstance(validation_results, dict):
                        for manifest_label, result_obj in validation_results.items():
                            if isinstance(result_obj, dict):
                                failures = result_obj.get("failure", [])
                                for failure in failures:
                                    code = failure.get("code") or ""
                                    validation_errors.append(failure)
                                    if "signingcredential" in code.lower():
                                        certificate_chain_valid = False
                                    if any(term in code.lower() for term in ["mismatch", "tampered", "missing", "invalid", "fail"]):
                                        tampering_indicators.append(f"Tampering detected in {manifest_label}: {code} - {failure.get('explanation', '')}")

                    details["certificate_chain_valid"] = certificate_chain_valid
                    details["validation_errors"] = validation_errors

                    # signature validity is determined by whether we have signature errors or invalid validation state
                    c2pa_valid = True
                    if validation_state and str(validation_state).lower() not in ["valid", "success"]:
                        if str(validation_state).lower() in ["invalid", "error", "fail", "tampered"]:
                            c2pa_valid = False

                    if tampering_indicators:
                        c2pa_valid = False

                    details["c2pa_valid"] = c2pa_valid
                    details["tampering_indicators"] = tampering_indicators
                    details["validation_status"] = str(validation_state) if validation_state else ("Valid" if c2pa_valid else "Invalid")

                    # Scored evidence logic
                    if not c2pa_valid:
                        evidence_score = 0.8
                        confidence = 0.99
                        details["evidence_summary"] = [
                            "C2PA Content Credentials found",
                            "Signature is invalid or tampered",
                            "Possible metadata tampering detected"
                        ]
                    else:
                        confidence = 0.99
                        if is_ai:
                            evidence_score = 1.0
                            details["evidence_summary"] = [
                                "C2PA Content Credentials found",
                                "Cryptographic signature is valid",
                                f"AI generation assertion found (Generator: {generator or 'Unknown AI'})"
                            ]
                        else:
                            evidence_score = 0.0
                            details["evidence_summary"] = [
                                "C2PA Content Credentials found",
                                "Cryptographic signature is valid",
                                "No AI generation assertion found"
                            ]

                    return {
                        "score": evidence_score,
                        "confidence": confidence,
                        "details": details
                    }

        except Exception as e:
            err_msg = str(e)
            if any(term in err_msg for term in ["ManifestNotFound", "no manifest", "not found"]):
                details["error"] = "No C2PA manifest found in the asset."
            else:
                details["error"] = f"C2PA reader error: {err_msg}"

        details["evidence_summary"] = ["No C2PA Content Credentials found"]
        return {
            "score": 0.0,
            "confidence": 0.0,
            "details": details
        }
