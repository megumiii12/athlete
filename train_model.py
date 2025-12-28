"""
Train and save the health AI model
Run this once to create health_model.pkl
"""

import numpy as np
import joblib
from sklearn.tree import DecisionTreeClassifier
import os

# Training data: [heart_rate, temperature, age]
X_train = np.array([
    # Young athletes (13-25) - Normal readings
    [65, 36.5, 18],
    [70, 36.8, 20],
    [75, 37.0, 22],
    [68, 36.9, 19],
    [72, 37.1, 21],
    [80, 37.2, 23],
    [78, 36.7, 20],
    [60, 36.4, 18],
    [85, 37.0, 24],
    [90, 36.9, 25],
    
    # Adult athletes (26-40) - Normal readings
    [70, 36.6, 30],
    [75, 36.9, 32],
    [80, 37.1, 35],
    [68, 36.8, 28],
    [85, 37.0, 38],
    
    # Mature athletes (41-60) - Normal readings
    [75, 36.7, 45],
    [80, 36.9, 50],
    [70, 36.8, 55],
    
    # Senior athletes (60+) - Normal readings
    [75, 36.8, 65],
    [80, 36.9, 70],
    
    # Young - Abnormal (High HR)
    [120, 37.0, 18],
    [130, 37.1, 22],
    [150, 37.2, 20],
    
    # Adult - Abnormal (High HR)
    [120, 37.0, 30],
    [140, 37.1, 35],
    
    # Mature - Abnormal (High HR)
    [130, 37.0, 45],
    [145, 37.1, 55],
    
    # Senior - Abnormal (High HR)
    [130, 37.0, 65],
    [145, 37.1, 70],
    
    # Abnormal Temperature (all ages)
    [80, 37.6, 20],
    [75, 37.8, 30],
    [85, 38.0, 45],
    [90, 38.5, 55],
    [95, 39.0, 65],
    
    # Both high (all ages)
    [120, 38.5, 22],
    [130, 38.8, 35],
    [140, 39.0, 50],
    
    # Low readings
    [45, 36.8, 20],
    [50, 36.9, 30],
    [75, 35.8, 40],
    [80, 35.5, 50],
])

# Labels: 0=normal, 1=abnormal
y_train = np.array([
    # Young athletes (13-25) - Normal readings (10 samples)
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    
    # Adult athletes (26-40) - Normal readings (5 samples)
    0, 0, 0, 0, 0,
    
    # Mature athletes (41-60) - Normal readings (3 samples)
    0, 0, 0,
    
    # Senior athletes (60+) - Normal readings (2 samples)
    0, 0,
    
    # Young - Abnormal (High HR) (3 samples)
    1, 1, 1,
    
    # Adult - Abnormal (High HR) (2 samples)
    1, 1,
    
    # Mature - Abnormal (High HR) (2 samples)
    1, 1,
    
    # Senior - Abnormal (High HR) (2 samples)
    1, 1,
    
    # Abnormal Temperature (all ages) (5 samples)
    1, 1, 1, 1, 1,
    
    # Both high (all ages) (3 samples)
    1, 1, 1,
    
    # Low readings (4 samples)
    1, 1, 1, 1,
])

print("🧠 Training AI Model...")
print(f"📊 Training samples: {len(X_train)}")
print(f"📈 Features: Heart Rate, Temperature, Age")

# Train the model
model = DecisionTreeClassifier(
    max_depth=5,
    min_samples_split=2,
    min_samples_leaf=1,
    random_state=42
)
model.fit(X_train, y_train)

# Test the model
test_accuracy = model.score(X_train, y_train)
print(f"✅ Model accuracy on training data: {test_accuracy:.2%}")

# Save the model
model_path = "health_model.pkl"
joblib.dump(model, model_path)
print(f"💾 Model saved to: {model_path}")

# Test predictions
print("\n🧪 Test predictions:")
test_cases = [
    ([75, 36.8, 25], "Normal readings"),
    ([120, 38.5, 25], "High HR & Temp (Abnormal)"),
    ([50, 36.5, 25], "Low HR (Abnormal)"),
    ([80, 35.2, 25], "Low Temp (Abnormal)"),
]

for features, description in test_cases:
    prediction = model.predict([features])[0]
    proba = model.predict_proba([features])[0]
    status = "🟢 NORMAL" if prediction == 0 else "🔴 ABNORMAL"
    print(f"{status} - {description}")
    print(f"   Confidence: {max(proba):.1%}")

print("\n✅ Model training complete! You can now run the Flask app.")