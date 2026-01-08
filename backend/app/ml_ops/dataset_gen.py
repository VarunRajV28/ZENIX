"""
Synthetic Maternal Health Dataset Generator
============================================
Generates 20,000 realistic maternal health records for ML model training.

Features to Generate:
- Age: Normal distribution (mean=28, std=6), range 15-60
- Systolic BP: Normal(120, 15) for low-risk, Normal(150, 20) for high-risk
- Diastolic BP: Normal(80, 10), ensure < systolic
- Blood Sugar: Log-normal(1.8, 0.3), range 3-15 mmol/L
- Body Temp: Normal(37, 0.5), range 36-39°C
- Heart Rate: Normal(80, 12), range 60-110
- Gestational Weeks: Uniform(1, 42)
- RiskLevel: Categorical (40% LOW, 35% MEDIUM, 20% HIGH, 5% CRITICAL)

Correlation Rules:
- High BP → Higher risk
- Age >35 → 1.5x risk multiplier
- Blood sugar >7.8 → Gestational diabetes indicator
- Weeks >40 → Increased risk
"""

import numpy as np
import pandas as pd
from pathlib import Path

# Set random seed for reproducibility
np.random.seed(42)

def generate_maternal_health_dataset(n_samples=20000):
    """
    Generate synthetic maternal health dataset.
    
    Args:
        n_samples: Number of samples to generate
    
    Returns:
        pandas DataFrame with maternal health data
    """
    print(f"Generating {n_samples} synthetic maternal health records...")
    
    data = []
    
    # Risk level distribution
    risk_distribution = {
        'LOW': 0.40,
        'MEDIUM': 0.35,
        'HIGH': 0.20,
        'CRITICAL': 0.05
    }
    
    for i in range(n_samples):
        # Randomly select risk level based on distribution
        risk_level = np.random.choice(
            list(risk_distribution.keys()),
            p=list(risk_distribution.values())
        )
        
        # Generate features based on risk level
        if risk_level == 'LOW':
            age = int(np.clip(np.random.normal(26, 5), 18, 34))
            systolic_bp = int(np.clip(np.random.normal(115, 10), 90, 130))
            diastolic_bp = int(np.clip(np.random.normal(75, 8), 60, 85))
            blood_sugar = np.clip(np.random.lognormal(1.7, 0.2), 3.5, 7.0)
            body_temp = np.clip(np.random.normal(36.8, 0.3), 36.2, 37.5)
            heart_rate = int(np.clip(np.random.normal(75, 8), 60, 90))
            blood_oxygen = np.clip(np.random.normal(98, 1), 95, 100)
            gestational_weeks = int(np.random.uniform(12, 40))
        
        elif risk_level == 'MEDIUM':
            age = int(np.clip(np.random.normal(32, 6), 25, 40))
            systolic_bp = int(np.clip(np.random.normal(130, 12), 120, 145))
            diastolic_bp = int(np.clip(np.random.normal(82, 10), 75, 92))
            blood_sugar = np.clip(np.random.lognormal(1.9, 0.3), 5.5, 9.0)
            body_temp = np.clip(np.random.normal(37.0, 0.4), 36.5, 38.0)
            heart_rate = int(np.clip(np.random.normal(82, 10), 70, 100))
            blood_oxygen = np.clip(np.random.normal(96, 2), 92, 100)
            gestational_weeks = int(np.random.choice([
                np.random.uniform(8, 12),   # Early pregnancy
                np.random.uniform(38, 42)    # Late/post-term
            ]))
        
        elif risk_level == 'HIGH':
            age = int(np.clip(np.random.normal(36, 5), 30, 45))
            systolic_bp = int(np.clip(np.random.normal(145, 15), 135, 165))
            diastolic_bp = int(np.clip(np.random.normal(92, 10), 85, 105))
            blood_sugar = np.clip(np.random.lognormal(2.0, 0.3), 7.5, 12.0)
            body_temp = np.clip(np.random.normal(37.5, 0.5), 37.0, 38.8)
            heart_rate = int(np.clip(np.random.normal(95, 12), 85, 115))
            blood_oxygen = np.clip(np.random.normal(94, 2), 90, 98)
            gestational_weeks = int(np.random.uniform(6, 42))
        
        else:  # CRITICAL
            age = int(np.clip(np.random.normal(38, 6), 32, 50))
            systolic_bp = int(np.clip(np.random.normal(160, 20), 145, 200))
            diastolic_bp = int(np.clip(np.random.normal(105, 12), 92, 130))
            blood_sugar = np.clip(np.random.lognormal(2.2, 0.4), 2.0, 20.0)
            body_temp = np.clip(np.random.normal(38.2, 0.8), 37.5, 40.0)
            heart_rate = int(np.clip(np.random.normal(115, 15), 100, 150))
            blood_oxygen = np.clip(np.random.normal(90, 3), 75, 95)
            gestational_weeks = int(np.random.uniform(4, 42))
        
        # Ensure systolic > diastolic
        if systolic_bp <= diastolic_bp:
            systolic_bp = diastolic_bp + np.random.randint(15, 30)
        
        # Create record
        record = {
            'Age': age,
            'SystolicBP': systolic_bp,
            'DiastolicBP': diastolic_bp,
            'BloodSugar': round(blood_sugar, 1),
            'BodyTemp': round(body_temp, 1),
            'HeartRate': heart_rate,
            'BloodOxygen': round(blood_oxygen, 1),
            'GestationalWeeks': gestational_weeks,
            'RiskLevel': risk_level
        }
        
        data.append(record)
        
        if (i + 1) % 5000 == 0:
            print(f"Generated {i + 1}/{n_samples} records...")
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Print statistics
    print("\n" + "="*60)
    print("Dataset Statistics:")
    print("="*60)
    print(f"Total records: {len(df)}")
    print(f"\nRisk Level Distribution:")
    print(df['RiskLevel'].value_counts(normalize=True).sort_index())
    print(f"\nFeature Statistics:")
    print(df.describe())
    print("="*60)
    
    return df


if __name__ == "__main__":
    # Create data directory
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    
    # Generate dataset
    dataset = generate_maternal_health_dataset(n_samples=20000)
    
    # Save to CSV
    output_path = data_dir / "maternal_health_dataset.csv"
    dataset.to_csv(output_path, index=False)
    
    print(f"\n✓ Dataset saved to: {output_path}")
    print(f"✓ Total records: {len(dataset)}")
    print("\nNext steps:")
    print("1. Review the dataset: pandas.read_csv('data/maternal_health_dataset.csv')")
    print("2. Train the model: python train.py")
