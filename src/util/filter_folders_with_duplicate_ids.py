import os

path = "dataset/Student_Dataset"
folders = [folder for folder in os.listdir(path) if os.path.isdir(os.path.join(path, folder))]

# Dictionary to store encountered IDs
id_dict = {}

print("Folders with duplicate IDs:")
print()
for folder in folders:
    # Extracting ID from folder name
    folder_id = folder.split('_')[-1]  # Using -1 to get the last element
    
    # Check if ID is already encountered
    if folder_id in id_dict:
        print("Duplicate ID:", folder_id)
        print("Folder 1:", id_dict[folder_id])
        print("Folder 2:", folder)
        print()
    else:
        id_dict[folder_id] = folder
