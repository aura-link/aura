import re

with open("/home/yesswera/YessweraWeb/server_jwt.py", "r") as f:
    content = f.read()

# Buscar y reemplazar la función generate_order_codes
old_pattern = r'def generate_order_codes\(\):.*?return pickup_code, delivery_code'

new_func = '''def generate_order_codes():
    """Generate verification codes for secure order flow

    Returns:
        Tuple of (driver_code, comanda_code, delivery_code)
        - driver_code: 4 chars - Repartidor dice este codigo al negocio
        - comanda_code: 4 chars - Identificador de comanda/pedido fisico en negocio
        - delivery_code: 5 chars - Cliente dice este codigo al repartidor
    """
    driver_code = generate_verification_code(4)    # Repartidor -> Negocio
    comanda_code = generate_verification_code(4)   # ID interno del negocio
    delivery_code = generate_verification_code(5)  # Cliente -> Repartidor

    # Ensure all codes are different
    codes = [driver_code, comanda_code, delivery_code]
    while len(codes) != len(set(codes)):
        driver_code = generate_verification_code(4)
        comanda_code = generate_verification_code(4)
        delivery_code = generate_verification_code(5)
        codes = [driver_code, comanda_code, delivery_code]

    return driver_code, comanda_code, delivery_code'''

content = re.sub(old_pattern, new_func, content, flags=re.DOTALL)

with open("/home/yesswera/YessweraWeb/server_jwt.py", "w") as f:
    f.write(content)

print("Funcion actualizada")
