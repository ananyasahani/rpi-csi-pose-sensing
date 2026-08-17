import os
import numpy as np
import matplotlib.pyplot as plt

# 1. Define paths
base_path = os.path.expanduser("~/.cache/kagglehub/datasets/hylanj/wifi-csi-dataset-ut-har/versions/1")
data_path = os.path.join(base_path, "data", "X_train.csv")
label_path = os.path.join(base_path, "label", "y_train.csv")

print(f"Loading data from {base_path}...")

# 2. Load using np.load() despite the .csv extension
try:
    X_train = np.load(data_path, allow_pickle=True)
    y_train = np.load(label_path, allow_pickle=True)
except Exception as e:
    print(f"Failed to load: {e}")
    exit()

print(f"X_train shape: {X_train.shape}")
print(f"y_train shape: {y_train.shape}")

# 3. Standard UT-HAR activity mapping
activities = {
    0: 'Lie down', 
    1: 'Fall', 
    2: 'Walk', 
    3: 'Pick up', 
    4: 'Run', 
    5: 'Sit down', 
    6: 'Stand up'
}

num_classes = len(activities)
fig, axes = plt.subplots(num_classes, 1, figsize=(10, 16), sharex=False)
fig.suptitle("UT-HAR CSI Amplitude Signatures by Activity", fontsize=16)

SUBCARRIERS = 90
y_train_flat = y_train.flatten()

for label_idx in range(num_classes):
    ax = axes[label_idx]
    
    matching_indices = np.where(y_train_flat == label_idx)[0]
    if len(matching_indices) == 0:
        ax.set_title(f"Activity: {activities[label_idx]} (No Data Found)")
        ax.axis('off')
        continue
        
    sample_idx = matching_indices[0]
    sample_data = X_train[sample_idx]
    
    sample_data_flat = sample_data.flatten()
    features_len = len(sample_data_flat)
    
    if features_len % SUBCARRIERS == 0:
        time_steps = features_len // SUBCARRIERS
        csi_matrix = sample_data_flat.reshape((time_steps, SUBCARRIERS)).T
        
        im = ax.imshow(csi_matrix, aspect='auto', cmap='viridis', origin='lower')
        ax.set_title(f"{activities[label_idx]} (Label {label_idx}) - Heatmap")
        ax.set_ylabel("Subcarrier Index")
        if label_idx == num_classes - 1:
            ax.set_xlabel("Time Steps")
    else:
        ax.plot(sample_data_flat, color='tab:blue', linewidth=0.5)
        ax.set_title(f"{activities[label_idx]} (Label {label_idx}) - 1D Flattened")
        ax.set_ylabel("Amplitude")
        if label_idx == num_classes - 1:
            ax.set_xlabel("Flattened Features")

plt.tight_layout(rect=[0, 0, 1, 0.98])

# --- SAVING LOGIC ---
# Create the plots directory if it doesn't exist
os.makedirs('plots', exist_ok=True)
save_path = os.path.join('plots', 'csi_heatmaps.png')

# Save the figure instead of showing it
plt.savefig(save_path, dpi=300, bbox_inches='tight')
print(f"Plot successfully saved to: {os.path.abspath(save_path)}")

# Clear memory to prevent headless memory leaks
plt.close()
