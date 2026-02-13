with open("/home/yesswera/YessweraWeb/server_jwt.py", "r") as f:
    content = f.read()

# Add driver_verified to active statuses
old_statuses = "'pending', 'confirmed', 'preparing', 'ready', 'accepted', 'assigned', 'in_transit', 'picked_up',"
new_statuses = "'pending', 'confirmed', 'preparing', 'ready', 'accepted', 'assigned', 'driver_verified', 'in_transit', 'picked_up',"

content = content.replace(old_statuses, new_statuses)

with open("/home/yesswera/YessweraWeb/server_jwt.py", "w") as f:
    f.write(content)

print("Status driver_verified agregado a active_statuses")
