import os
import pandas as pd

# Get the directory of the current Python script
current_dir = os.path.dirname(__file__)

# Construct the file paths
biohazard_path = os.path.join(current_dir, 'preprocessed_data/biohazard.csv')
conflict_path = os.path.join(current_dir, 'preprocessed_data/conflict.csv')
earthquake_path = os.path.join(current_dir, 'preprocessed_data/earthquake.csv')
fire_path = os.path.join(current_dir, 'preprocessed_data/fire.csv')
typhoon_path = os.path.join(current_dir, 'preprocessed_data/typhoon.csv')
volcanic_path = os.path.join(current_dir, 'preprocessed_data/volcanic.csv')

# Read the CSV files
biohazard = pd.read_csv(biohazard_path)
conflict = pd.read_csv(conflict_path)
earthquake = pd.read_csv(earthquake_path)
fire = pd.read_csv(fire_path)
typhoon = pd.read_csv(typhoon_path)
volcanic = pd.read_csv(volcanic_path)
