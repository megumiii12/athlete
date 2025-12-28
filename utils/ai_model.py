import os
import numpy as np
import joblib
from sklearn.tree import DecisionTreeClassifier

class HealthAIModel:
    def __init__(self):
        self.model_path = "health_model.pkl"
        self.model = None
        if os.path.exists(self.model_path):
            self.load_model()
        else:
            raise FileNotFoundError("health_model.pkl not found. Please train and save it first.")

    def load_model(self):
        self.model = joblib.load(self.model_path)

    def predict(self, heart_rate, temperature, age=25):
        """
        Predict if health readings are abnormal based on age-adjusted thresholds.
        
        Age categories:
        - Young (13-25): Lower baseline, athletic norms
        - Adult (26-40): Standard norms
        - Mature (41-60): Higher baseline acceptable
        - Senior (60+): More lenient thresholds
        """
        if not self.model:
            self.load_model()

        features = np.array([[heart_rate, temperature, age]])
        prediction = self.model.predict(features)[0]
        proba = self.model.predict_proba(features)[0]
        
        # Get age-adjusted alert message
        alert_msg = self._alert_message(heart_rate, temperature, age)
        
        return {
            "is_abnormal": int(prediction),
            "confidence": float(max(proba)),
            "alert_message": alert_msg,
            "heart_rate": heart_rate,
            "temperature": temperature,
            "age": age
        }

    def _alert_message(self, hr, temp, age):
        """
        Generate alert messages based on age-adjusted thresholds.
        Different age groups have different normal ranges.
        """
        alerts = []
        
        # Age-adjusted heart rate thresholds
        if age < 26:  # Young athletes (13-25)
            hr_high = 160
            hr_low = 45
        elif age < 41:  # Adults (26-40)
            hr_high = 155
            hr_low = 50
        elif age < 61:  # Mature (41-60)
            hr_high = 145
            hr_low = 55
        else:  # Seniors (60+)
            hr_high = 130
            hr_low = 60
        
        # Age-adjusted temperature thresholds
        if age < 26:
            temp_high = 38.5
            temp_low = 35.8
        elif age < 41:
            temp_high = 38.2
            temp_low = 35.9
        elif age < 61:
            temp_high = 37.9
            temp_low = 36.0
        else:
            temp_high = 37.6
            temp_low = 36.1
        
        # Check heart rate
        if hr > hr_high:
            alerts.append(f"High heart rate ({hr:.0f} BPM)")
        elif hr < hr_low:
            alerts.append(f"Low heart rate ({hr:.0f} BPM)")
        
        # Check temperature
        if temp > temp_high:
            alerts.append(f"High temperature ({temp:.1f} °C)")
        elif temp < temp_low:
            alerts.append(f"Low temperature ({temp:.1f} °C)")
        
        return " | ".join(alerts) if alerts else "Normal readings"