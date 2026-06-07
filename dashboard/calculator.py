from __future__ import annotations
from typing import Any

def compute_bmr_bmi(cleaned: dict[str, Any]) -> dict[str, Any]:
    w = float(cleaned['weight_kg'])
    h_cm = float(cleaned['height_cm'])
    age = int(cleaned['age'])
    sex = cleaned['sex']
    activity = float(cleaned['activity'])
    if sex == 'm':
        bmr = 10 * w + 6.25 * h_cm - 5 * age + 5
    else:
        bmr = 10 * w + 6.25 * h_cm - 5 * age - 161
    tdee = bmr * activity
    h_m = h_cm / 100.0
    bmi = w / (h_m * h_m)

    def bmi_zone(b: float) -> str:
        if b < 18.5:
            return 'Недостаточный вес'
        if b < 25:
            return 'Норма'
        if b < 30:
            return 'Избыточный вес'
        return 'Ожирение'
    return {'bmr': round(bmr), 'tdee': round(tdee), 'bmi': round(bmi, 1), 'bmi_zone': bmi_zone(bmi), 'activity_factor': activity}
