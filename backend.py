# === BACKEND.PY ===
# Backend API para el sistema de restaurante con integración de FastAPI y PostgreSQL.

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime, date, timedelta

# IMPORTAR LA SUB-APP DE INVENTARIO
from inventario_backend import inventario_app
from configuraciones_backend import configuraciones_app
from fastapi import Query 
from fastapi import FastAPI, HTTPException, Depends, Query # Asegúrate de tener Query importado
from recetas_backend import recetas_app


app = FastAPI(title="RestaurantIA Backend")

# Montar la sub-app de inventario
app.mount("/inventario", inventario_app)
app.mount("/configuraciones", configuraciones_app)
app.mount("/recetas", recetas_app)


# Configuración directa de PostgreSQL
DATABASE_URL = "dbname=restaurant_db user=postgres password=postgres host=localhost port=5432"

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API del Sistema de Restaurante"}

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()

# Modelos
class ItemMenu(BaseModel):
    nombre: str
    precio: float
    tipo: str

class PedidoCreate(BaseModel):
    mesa_numero: int
    items: List[dict]
    estado: str = "Pendiente"
    notas: str = ""

class PedidoResponse(BaseModel):
    id: int
    mesa_numero: int
    items: List[dict]
    estado: str
    fecha_hora: str
    numero_app: Optional[int] = None
    notas: str = ""

class ClienteCreate(BaseModel):
    nombre: str
    domicilio: str
    celular: str

class ClienteResponse(BaseModel):
    id: int
    nombre: str
    domicilio: str
    celular: str
    fecha_registro: str
    
class ReservaCreate(BaseModel):
    mesa_numero: int
    cliente_id: int
    fecha_hora_inicio: str  # "YYYY-MM-DD HH:MM:SS"
    fecha_hora_fin: Optional[str] = None # "YYYY-MM-DD HH:MM:SS"

# Endpoints
@app.get("/health")
def health():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.close()
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)}

@app.get("/menu/items", response_model=List[ItemMenu])
def obtener_menu(conn: psycopg2.extensions.connection = Depends(get_db)):
    with conn.cursor() as cursor:
        cursor.execute("SELECT nombre, precio, tipo FROM menu ORDER BY tipo, nombre")
        items = cursor.fetchall()
        return items

@app.post("/pedidos", response_model=PedidoResponse)
def crear_pedido(pedido: PedidoCreate, conn: psycopg2.extensions.connection = Depends(get_db)):
    with conn.cursor() as cursor:
        numero_app = None
        if pedido.mesa_numero == 99:
            cursor.execute("SELECT MAX(numero_app) FROM pedidos WHERE mesa_numero = 99")
            max_app = cursor.fetchone()
            if max_app and max_app['max'] is not None:
                numero_app = max_app['max'] + 1
            else:
                numero_app = 1

        fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO pedidos (mesa_numero, numero_app, estado, fecha_hora, items, notas)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, mesa_numero, numero_app, estado, fecha_hora, items, notas
        """, (
            pedido.mesa_numero,
            numero_app,
            pedido.estado,
            fecha_hora,
            json.dumps(pedido.items),
            pedido.notas
        ))
        
        result = cursor.fetchone()
        
        # --- NUEVA LÓGICA: CONSUMIR INGREDIENTES DE LAS RECETAS (MANEJANDO CANTIDAD DEL PEDIDO) ---
        # Suponiendo que 'cursor' es el cursor de la conexión activa en crear_pedido
        # Agrupar items por nombre para calcular cantidades totales
        items_agrupados = {}
        for item in pedido.items:
            nombre_item = item['nombre']
            if nombre_item in items_agrupados:
                items_agrupados[nombre_item] += 1
            else:
                items_agrupados[nombre_item] = 1

        for nombre_item, cantidad_pedido in items_agrupados.items():
            # Buscar si el ítem del pedido tiene una receta asociada
            cursor.execute("""
                SELECT r.id
                FROM recetas r
                WHERE r.nombre_plato = %s
            """, (nombre_item,))
            receta = cursor.fetchone()
            if receta:
                # Si tiene receta, obtener los ingredientes necesarios
                cursor.execute("""
                    SELECT ir.ingrediente_id, ir.cantidad_necesaria
                    FROM ingredientes_recetas ir
                    WHERE ir.receta_id = %s
                """, (receta['id'],))
                for ing in cursor.fetchall():
                    # Calcular cantidad total a consumir basada en la cantidad del pedido
                    cantidad_a_consumir = ing['cantidad_necesaria'] * cantidad_pedido
                    # Restar la cantidad necesaria del inventario
                    # OJO: Esta operación simple puede causar cantidades negativas si no hay suficiente stock.
                    # En una implementación robusta, se debería verificar el stock antes de restar
                    # o manejar el error si la cantidad disponible es menor que la necesaria.
                    cursor.execute("""
                        UPDATE inventario
                        SET cantidad_disponible = cantidad_disponible - %s
                        WHERE id = %s
                    """, (cantidad_a_consumir, ing['ingrediente_id']))
        # --- FIN NUEVA LÓGICA ---
        
        conn.commit()
        # ✅ CORREGIDO: Convertir datetime a string si es necesario
        fecha_hora_str = result['fecha_hora'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(result['fecha_hora'], datetime) else result['fecha_hora']
        
        return {
            "id": result['id'],
            "mesa_numero": result['mesa_numero'],
            "items": result['items'],
            "estado": result['estado'],
            "fecha_hora": fecha_hora_str,
            "numero_app": result['numero_app'],
            "notas": result['notas']
        }

@app.get("/pedidos/activos", response_model=List[PedidoResponse])
def obtener_pedidos_activos(conn: psycopg2.extensions.connection = Depends(get_db)):
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT id, mesa_numero, numero_app, estado, fecha_hora, items, notas 
            FROM pedidos 
            WHERE estado IN ('Pendiente', 'En preparacion', 'Listo')
            ORDER BY fecha_hora DESC
        """)
        pedidos = []
        for row in cursor.fetchall():
            # ✅ CORREGIDO: Convertir datetime a string si es necesario
            fecha_hora_str = row['fecha_hora'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(row['fecha_hora'], datetime) else row['fecha_hora']
            pedidos.append({
                "id": row['id'],
                "mesa_numero": row['mesa_numero'],
                "numero_app": row['numero_app'],
                "estado": row['estado'],
                "fecha_hora": fecha_hora_str,
                "items": row['items'],
                "notas": row['notas']
            })
        return pedidos

# --- MODIFICACIÓN EN EL ENDPOINT DE ACTUALIZACIÓN DE ESTADO ---
@app.patch("/pedidos/{pedido_id}/estado")
def actualizar_estado_pedido(pedido_id: int, estado: str, conn = Depends(get_db)):
    with conn.cursor() as cursor:
        # Verificar si el pedido existe
        cursor.execute("SELECT estado, hora_inicio_cocina, hora_fin_cocina FROM pedidos WHERE id = %s", (pedido_id,))
        pedido = cursor.fetchone()
        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")

        # --- LÓGICA PARA REGISTRAR MARCAS DE TIEMPO ---
        now = datetime.now()
        extra_update = ""
        extra_values = []

        if estado == "En preparacion" and pedido['hora_inicio_cocina'] is None:
            # Solo registrar si es la primera vez que entra en "En preparacion"
            extra_update = ", hora_inicio_cocina = %s"
            extra_values.append(now)
        elif estado == "Listo" and pedido['hora_inicio_cocina'] is not None and pedido['hora_fin_cocina'] is None:
            # Registrar fin solo si hay un inicio registrado y aún no se ha registrado el fin
            extra_update = ", hora_fin_cocina = %s"
            extra_values.append(now)
        # Opcional: Podrías limpiar hora_inicio_cocina si el estado vuelve a "Pendiente", pero eso complica la lógica.
        # --- FIN LÓGICA ---

        # Actualizar el estado (y potencialmente las marcas de tiempo)
        update_query = f"UPDATE pedidos SET estado = %s {extra_update} WHERE id = %s RETURNING id, mesa_numero, cliente_id, estado, fecha_hora, items, numero_app, notas, updated_at, hora_inicio_cocina, hora_fin_cocina"
        cursor.execute(update_query, (estado, *extra_values, pedido_id)) # *extra_values para desempaquetar los valores opcionales
        result = cursor.fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")

        conn.commit()

        # Devolver el pedido actualizado
        pedido_dict = dict(result)
        # Opcional: Calcular el tiempo transcurrido aquí si se envía al cliente
        if pedido_dict['hora_inicio_cocina'] and pedido_dict['hora_fin_cocina']:
            tiempo_cocina = (pedido_dict['hora_fin_cocina'] - pedido_dict['hora_inicio_cocina']).total_seconds() / 60 # En minutos
            pedido_dict['tiempo_cocina_minutos'] = tiempo_cocina
        elif pedido_dict['hora_inicio_cocina'] and estado == "Listo": # Solo si se acaba de marcar como listo y hay inicio
             tiempo_cocina = (now - pedido_dict['hora_inicio_cocina']).total_seconds() / 60 # En minutos
             pedido_dict['tiempo_cocina_minutos'] = tiempo_cocina

        return pedido_dict
# --- FIN MODIFICACIÓN ---

@app.get("/mesas")
def obtener_mesas(conn: psycopg2.extensions.connection = Depends(get_db)):
    """
    Obtiene el estado real de todas las mesas desde la base de datos.
    """
    try:
        with conn.cursor() as cursor:
            # ✅ ENFOQUE SIMPLIFICADO: Obtener mesas y verificar ocupación por separado
            mesas_result = []
            
            # Definir las mesas físicas
            mesas_fisicas = [
                {"numero": 1, "capacidad": 2},
                {"numero": 2, "capacidad": 2},
                {"numero": 3, "capacidad": 4},
                {"numero": 4, "capacidad": 4},
                {"numero": 5, "capacidad": 6},
                {"numero": 6, "capacidad": 6},
            ]
            
            for mesa in mesas_fisicas:
                # Verificar si la mesa tiene pedidos activos
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM pedidos 
                    WHERE mesa_numero = %s 
                    AND estado IN ('Pendiente', 'En preparacion', 'Listo')
                """, (mesa["numero"],))
                
                result = cursor.fetchone()
                # ✅ CORREGIDO: Asegurar que el conteo sea entero y no None
                count = result['count'] if result and result['count'] is not None else 0
                print(f"Mesa {mesa['numero']} -> COUNT: {count}")  # DEBUG
                ocupada = count > 0
                
                mesas_result.append({
                    "numero": mesa["numero"],
                    "capacidad": mesa["capacidad"],
                    "ocupada": ocupada  # ← Este valor se envía al frontend
                })
            
            # Agregar mesa virtual
            mesas_result.append({
                "numero": 99,
                "capacidad": 1,
                "ocupada": False,
                "es_virtual": True
            })
            
            return mesas_result
            
    except Exception as e:
        print(f"Error en obtener_mesas: {e}")
        # En caso de error, devolver mesas por defecto como LIBRES
        return [
            {"numero": 1, "capacidad": 2, "ocupada": False},
            {"numero": 2, "capacidad": 2, "ocupada": False},
            {"numero": 3, "capacidad": 4, "ocupada": False},
            {"numero": 4, "capacidad": 4, "ocupada": False},
            {"numero": 5, "capacidad": 6, "ocupada": False},
            {"numero": 6, "capacidad": 6, "ocupada": False},
            {"numero": 99, "capacidad": 1, "ocupada": False, "es_virtual": True}
        ]

# Endpoint para inicializar menú
@app.post("/menu/inicializar")
def inicializar_menu(conn: psycopg2.extensions.connection = Depends(get_db)):
    menu_inicial = [
        # Entradas
        ("Empanada Kunai", 70.00, "Entradas"),
        ("Dedos de queso (5pz)", 75.00, "Entradas"),
        ("Chile Relleno", 60.00, "Entradas"),
        ("Caribe Poppers", 130.00, "Entradas"),
        ("Brocheta", 50.00, "Entradas"),
        ("Rollos Primavera (2pz)", 100.00, "Entradas"),
        # Platillos
        ("Camarones roca", 160.00, "Platillos"),
        ("Teriyaki", 130.00, "Platillos"),
        ("Bonneles (300gr)", 150.00, "Platillos"),
        # Arroces
        ("Yakimeshi Especial", 150.00, "Arroces"),
        ("Yakimeshi Kunai", 140.00, "Arroces"),
        ("Yakimeshi Golden", 145.00, "Arroces"),
        ("Yakimeshi Horneado", 145.00, "Arroces"),
        ("Gohan Mixto", 125.00, "Arroces"),
        ("Gohan Crispy", 125.00, "Arroces"),
        ("Gohan Chicken", 120.00, "Arroces"),
        ("Kunai Burguer", 140.00, "Arroces"),
        ("Bomba", 105.00, "Arroces"),
        ("Bomba Especial", 135.00, "Arroces"),
        # Naturales
        ("Guamuchilito", 110.00, "Naturales"),
        ("Avocado", 125.00, "Naturales"),
        ("Grenudo Roll", 135.00, "Naturales"),
        ("Granja Roll", 115.00, "Naturales"),
        ("California Roll", 100.00, "Naturales"),
        ("California Especial", 130.00, "Naturales"),
        ("Arcoíris", 120.00, "Naturales"),
        ("Tuna Roll", 130.00, "Naturales"),
        ("Kusanagi", 130.00, "Naturales"),
        ("Kanisweet", 120.00, "Naturales"),
        # Empanizados
        ("Mar y Tierra", 95.00, "Empanizados"),
        ("Tres Quesos", 100.00, "Empanizados"),
        ("Cordon Blue", 105.00, "Empanizados"),
        ("Roka Roll", 135.00, "Empanizados"),
        ("Camarón Bacon", 110.00, "Empanizados"),
        ("Cielo, mar y tierra", 110.00, "Empanizados"),
        ("Konan Roll", 130.00, "Empanizados"),
        ("Pain Roll", 115.00, "Empanizados"),
        ("Sasori Roll", 125.00, "Empanizados"),
        ("Chikin", 130.00, "Empanizados"),
        ("Caribe Roll", 115.00, "Empanizados"),
        ("Chon", 120.00, "Empanizados"),
        # Gratinados
        ("Kunai Especial", 150.00, "Gratinados"),
        ("Chuma Roll", 145.00, "Gratinados"),
        ("Choche Roll", 140.00, "Gratinados"),
        ("Milán Roll", 135.00, "Gratinados"),
        ("Chio Roll", 145.00, "Gratinados"),
        ("Prime", 140.00, "Gratinados"),
        ("Ninja Roll", 135.00, "Gratinados"),
        ("Serranito", 135.00, "Gratinados"),
        ("Sanji", 145.00, "Gratinados"),
        ("Monkey Roll", 135.00, "Gratinados"),
        # Kunai Kids
        ("Baby Roll (8pz)", 60.00, "Kunai Kids"),
        ("Chicken Sweet (7pz)", 60.00, "Kunai Kids"),
        ("Chesse Puffs (10pz)", 55.00, "Kunai Kids"),
        # Bebidas
        ("Te refil", 35.00, "Bebidas"),
        ("Te de litro", 35.00, "Bebidas"),
        ("Coca-cola", 35.00, "Bebidas"),
        ("Agua natural", 20.00, "Bebidas"),
        ("Agua mineral", 35.00, "Bebidas"),
        # Extras
        ("Camaron", 20.00, "Extras"),
        ("Res", 15.00, "Extras"),
        ("Pollo", 15.00, "Extras"),
        ("Tocino", 15.00, "Extras"),
        ("Gratinado", 15.00, "Extras"),
        ("Aguacate", 25.00, "Extras"),
        ("Empanizado", 15.00, "Extras"),
        ("Philadelphia", 10.00, "Extras"),
        ("Tampico", 25.00, "Extras"),
        ("Siracha", 10.00, "Extras"),
        ("Soya", 10.00, "Extras"),
    ]
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM menu")
            for nombre, precio, tipo in menu_inicial:
                cursor.execute("""
                    INSERT INTO menu (nombre, precio, tipo)
                    VALUES (%s, %s, %s)
                """, (nombre, precio, tipo))
            conn.commit()
            return {"status": "ok", "items_insertados": len(menu_inicial)}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al inicializar menú: {str(e)}")

# ¡NUEVO ENDPOINT! → Eliminar último ítem de un pedido
@app.delete("/pedidos/{pedido_id}/ultimo_item")
def eliminar_ultimo_item(pedido_id: int, conn: psycopg2.extensions.connection = Depends(get_db)):
    with conn.cursor() as cursor:
        cursor.execute("SELECT items FROM pedidos WHERE id = %s", (pedido_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        
        items = json.loads(row['items'])
        if not items:
            raise HTTPException(status_code=400, detail="No hay ítems para eliminar")
        
        items.pop()
        cursor.execute("UPDATE pedidos SET items = %s WHERE id = %s", (json.dumps(items), pedido_id))
        conn.commit()
        return {"status": "ok"}

# ¡NUEVOS ENDPOINTS! → Gestión completa de pedidos y menú

@app.put("/pedidos/{pedido_id}")
def actualizar_pedido(pedido_id: int, pedido_actualizado: PedidoCreate, conn: psycopg2.extensions.connection = Depends(get_db)):
    with conn.cursor() as cursor:
        cursor.execute("SELECT id FROM pedidos WHERE id = %s", (pedido_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        
        fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE pedidos 
            SET mesa_numero = %s, estado = %s, fecha_hora = %s, items = %s, notas = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (
            pedido_actualizado.mesa_numero,
            pedido_actualizado.estado,
            fecha_hora,
            json.dumps(pedido_actualizado.items),
            pedido_actualizado.notas,
            pedido_id
        ))
        
        
        conn.commit()
        return {"status": "ok", "message": "Pedido actualizado"}

@app.delete("/pedidos/{pedido_id}")
def eliminar_pedido(pedido_id: int, conn: psycopg2.extensions.connection = Depends(get_db)):
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM pedidos WHERE id = %s", (pedido_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        conn.commit()
        return {"status": "ok", "message": "Pedido eliminado"}

@app.post("/menu/items")
def agregar_item_menu(item: ItemMenu, conn: psycopg2.extensions.connection = Depends(get_db)):
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO menu (nombre, precio, tipo)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (item.nombre, item.precio, item.tipo))
        item_id = cursor.fetchone()['id']
        conn.commit()
        return {"status": "ok", "id": item_id, "message": "Ítem agregado al menú"}

@app.delete("/menu/items")
def eliminar_item_menu(nombre: str, tipo: str, conn: psycopg2.extensions.connection = Depends(get_db)):
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM menu WHERE nombre = %s AND tipo = %s", (nombre, tipo))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Ítem no encontrado en el menú")
        conn.commit()
        return {"status": "ok", "message": "Ítem eliminado del menú"}

# NUEVOS ENDPOINTS PARA GESTIÓN DE CLIENTES

@app.get("/clientes", response_model=List[ClienteResponse])
def obtener_clientes(conn: psycopg2.extensions.connection = Depends(get_db)):
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, nombre, domicilio, celular, fecha_registro FROM clientes ORDER BY nombre")
        clientes = []
        for row in cursor.fetchall():
            fecha_str = row['fecha_registro'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(row['fecha_registro'], datetime) else row['fecha_registro']
            clientes.append({
                "id": row['id'],
                "nombre": row['nombre'],
                "domicilio": row['domicilio'],
                "celular": row['celular'],
                "fecha_registro": fecha_str
            })
        return clientes

@app.post("/clientes", response_model=ClienteResponse)
def crear_cliente(cliente: ClienteCreate, conn: psycopg2.extensions.connection = Depends(get_db)):
    with conn.cursor() as cursor:
        fecha_registro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO clientes (nombre, domicilio, celular)
            VALUES (%s, %s, %s)
            RETURNING id, nombre, domicilio, celular, fecha_registro
        """, (cliente.nombre, cliente.domicilio, cliente.celular))
        result = cursor.fetchone()
        conn.commit()
        fecha_str = result['fecha_registro'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(result['fecha_registro'], datetime) else result['fecha_registro']
        return {
            "id": result['id'],
            "nombre": result['nombre'],
            "domicilio": result['domicilio'],
            "celular": result['celular'],
            "fecha_registro": fecha_str
        }

@app.delete("/clientes/{cliente_id}")
def eliminar_cliente(cliente_id: int, conn: psycopg2.extensions.connection = Depends(get_db)):
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM clientes WHERE id = %s", (cliente_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        conn.commit()
        return {"status": "ok", "message": "Cliente eliminado"}
    
@app.get("/reportes")
def obtener_reporte(
    tipo: str,
    start_date: str,
    end_date: str,
    conn: psycopg2.extensions.connection = Depends(get_db)
):
    with conn.cursor() as cursor:
        # Consultar pedidos en el rango de fechas
        cursor.execute("""
            SELECT items, estado, fecha_hora
            FROM pedidos
            WHERE fecha_hora >= %s AND fecha_hora < %s
            AND estado IN ('Listo', 'Entregado', 'Pagado')
        """, (start_date, end_date))
        
        pedidos = cursor.fetchall()
        
        # Calcular estadísticas
        ventas_totales = 0
        pedidos_totales = len(pedidos)
        productos_vendidos = 0
        productos_mas_vendidos = {}

        for pedido in pedidos:
            # ✅ CORREGIR: El campo 'items' ya es una lista, no necesita json.loads()
            items = pedido['items']
            
            # ✅ VERIFICAR SI ES STRING Y PARSEAR SI ES NECESARIO
            if isinstance(items, str):
                items = json.loads(items)
            
            for item in items:
                nombre = item['nombre']
                precio = item['precio']
                
                ventas_totales += precio
                productos_vendidos += 1
                
                # Contar productos más vendidos
                if nombre in productos_mas_vendidos:
                    productos_mas_vendidos[nombre] += 1
                else:
                    productos_mas_vendidos[nombre] = 1

        # Ordenar productos más vendidos
        productos_mas_vendidos_lista = sorted(
            [{'nombre': k, 'cantidad': v} for k, v in productos_mas_vendidos.items()],
            key=lambda x: x['cantidad'],
            reverse=True
        )[:10]  # Top 10

        return {
            "ventas_totales": round(ventas_totales, 2),
            "pedidos_totales": pedidos_totales,
            "productos_vendidos": productos_vendidos,
            "productos_mas_vendidos": productos_mas_vendidos_lista
        }
        

@app.get("/analisis/productos")
def obtener_analisis_productos(
    start_date: str = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    end_date: str = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    conn: psycopg2.extensions.connection = Depends(get_db)
):
    """
    Obtiene el análisis de productos vendidos en un rango de fechas.
    """
    # Construir la condición de fecha si se proporcionan parámetros
    fecha_condicion = ""
    params = []
    if start_date and end_date:
        fecha_condicion = "AND fecha_hora >= %s AND fecha_hora < %s"
        params = [start_date, end_date]
    elif start_date:
        fecha_condicion = "AND fecha_hora >= %s"
        params = [start_date]
    elif end_date:
        # Si solo se da end_date, asumimos desde el principio de los tiempos hasta end_date
        fecha_condicion = "AND fecha_hora < %s"
        params = [end_date]

    with conn.cursor() as cursor:
        # Consultar ítems de pedidos en el rango de fechas y con estado de venta completada
        cursor.execute(f"""
            SELECT items
            FROM pedidos
            WHERE estado IN ('Entregado', 'Pagado') -- Ajustar según tu definición de venta completada
            {fecha_condicion}
        """, params)
        
        pedidos = cursor.fetchall()

    # Contar productos vendidos
    conteo_productos = {}
    for pedido in pedidos:
        # Asumiendo que 'items' es una lista de diccionarios
        items = pedido['items']
        if isinstance(items, str):
            items = json.loads(items) # Parsear si es string (aunque debería ser lista por el modelo de Pydantic o por cómo se inserta)

        if isinstance(items, list):
            for item in items:
                nombre = item.get('nombre')
                if nombre:
                    conteo_productos[nombre] = conteo_productos.get(nombre, 0) + 1

    # Ordenar productos
    productos_ordenados = sorted(conteo_productos.items(), key=lambda x: x[1], reverse=True)
    productos_mas_vendidos = [{"nombre": k, "cantidad": v} for k, v in productos_ordenados[:10]] # Top 10
    productos_menos_vendidos = [{"nombre": k, "cantidad": v} for k, v in productos_ordenados[-10:]] # Últimos 10 (menos vendidos)

    # Devolver el análisis
    return {
        "productos_mas_vendidos": productos_mas_vendidos,
        "productos_menos_vendidos": productos_menos_vendidos
    }


@app.get("/mesas")
def obtener_mesas_detalladas(conn = Depends(get_db)):
    """
    Obtiene el estado detallado de todas las mesas, incluyendo ocupación y reservas.
    """
    try:
        # Obtener mesas físicas desde la base de datos
        with conn.cursor() as cursor:
            cursor.execute("SELECT numero, capacidad FROM mesas WHERE numero != 99 ORDER BY numero;") # Excluir mesa virtual
            mesas_db = cursor.fetchall()

        # Obtener reservas activas (pueden ser para hoy o futuras, dependiendo de tu lógica)
        # Asumiendo una tabla 'reservas' con columnas: id, mesa_numero, cliente_id, fecha_hora_inicio, fecha_hora_fin
        # y una tabla 'clientes' con id, nombre
        with conn.cursor() as cursor:
            # Obtener reservas para hoy o futuras (puedes ajustar la lógica de fecha)
            from datetime import datetime, date # Importar aquí o asegurarte que esté arriba
            hoy = date.today().strftime("%Y-%m-%d")
            cursor.execute("""
                SELECT r.mesa_numero, r.fecha_hora_inicio, r.fecha_hora_fin, c.nombre as cliente_nombre
                FROM reservas r
                JOIN clientes c ON r.cliente_id = c.id
                WHERE DATE(r.fecha_hora_inicio) >= %s
                ORDER BY r.fecha_hora_inicio;
            """, (hoy,))
            reservas_db = cursor.fetchall()

        # Obtener pedidos activos para saber qué mesas están ocupadas
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT mesa_numero
                FROM pedidos
                WHERE estado IN ('Tomando pedido', 'Pendiente', 'En preparacion', 'Listo', 'Entregado')
                AND mesa_numero != 99; -- Excluir pedido digital
            """)
            pedidos_activos = set(row['mesa_numero'] for row in cursor.fetchall())

        # Combinar la información
        mesas_result = []
        reservas_por_mesa = {}
        for res in reservas_db:
            # Agrupar reservas por mesa (por si hay varias en un día)
            if res['mesa_numero'] not in reservas_por_mesa:
                reservas_por_mesa[res['mesa_numero']] = []
            reservas_por_mesa[res['mesa_numero']].append({
                "cliente_nombre": res['cliente_nombre'],
                "fecha_hora_inicio": str(res['fecha_hora_inicio']), # Convertir a string para JSON
                "fecha_hora_fin": str(res['fecha_hora_fin']) if res['fecha_hora_fin'] else None
            })

        for mesa_db in mesas_db:
            numero = mesa_db['numero']
            capacidad = mesa_db['capacidad']
            ocupada = numero in pedidos_activos
            reservada = numero in reservas_por_mesa

            mesa_info = {
                "numero": numero,
                "capacidad": capacidad,
                "ocupada": ocupada,
                "reservada": reservada,
                "cliente_reservado_nombre": None,
                "fecha_hora_reserva": None
            }

            if reservada:
                # Tomar la primera reserva encontrada para mostrar en la UI (puedes mejorar esta lógica)
                primera_reserva = reservas_por_mesa[numero][0]
                mesa_info["cliente_reservado_nombre"] = primera_reserva["cliente_nombre"]
                mesa_info["fecha_hora_reserva"] = primera_reserva["fecha_hora_inicio"]

            mesas_result.append(mesa_info)

        # Agregar mesa virtual (99)
        mesas_result.append({
            "numero": 99,
            "capacidad": 100, # o el valor que uses
            "ocupada": False, # La mesa virtual no se "ocupa" como las físicas
            "reservada": False, # Ni se "reserva"
            "cliente_reservado_nombre": None,
            "fecha_hora_reserva": None,
            "es_virtual": True # Opcional: para distinguirla en la UI
        })

        return mesas_result

    except Exception as e:
        print(f"Error en obtener_mesas_detalladas: {e}")
        # En caso de error, devolver mesas por defecto como lo hacía antes
        # Asegúrate de que esta estructura coincida con la que espera crear_mesas_grid
        return [
            {"numero": 1, "capacidad": 2, "ocupada": False, "reservada": False, "cliente_reservado_nombre": None, "fecha_hora_reserva": None},
            {"numero": 2, "capacidad": 2, "ocupada": False, "reservada": False, "cliente_reservado_nombre": None, "fecha_hora_reserva": None},
            {"numero": 3, "capacidad": 4, "ocupada": False, "reservada": False, "cliente_reservado_nombre": None, "fecha_hora_reserva": None},
            {"numero": 4, "capacidad": 4, "ocupada": False, "reservada": False, "cliente_reservado_nombre": None, "fecha_hora_reserva": None},
            {"numero": 5, "capacidad": 6, "ocupada": False, "reservada": False, "cliente_reservado_nombre": None, "fecha_hora_reserva": None},
            {"numero": 6, "capacidad": 6, "ocupada": False, "reservada": False, "cliente_reservado_nombre": None, "fecha_hora_reserva": None},
            {"numero": 99, "capacidad": 100, "ocupada": False, "reservada": False, "cliente_reservado_nombre": None, "fecha_hora_reserva": None, "es_virtual": True}
        ]

# Opcional: Endpoint para obtener mesas disponibles en una fecha/hora específica
@app.get("/mesas/disponibles/")
def obtener_mesas_disponibles_para_fecha_hora(
    fecha_hora_str: str = Query(..., description="Fecha y hora en formato YYYY-MM-DD HH:MM:SS"),
    conn = Depends(get_db)
):
    """
    Obtiene la lista de mesas disponibles para una fecha y hora específica.
    Una mesa está disponible si no está ocupada por un pedido activo ni reservada para esa hora.
    """
    from datetime import datetime
    try:
        fecha_hora_obj = datetime.strptime(fecha_hora_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha/hora inválido. Use YYYY-MM-DD HH:MM:SS")

    try:
        # Obtener mesas físicas
        with conn.cursor() as cursor:
            cursor.execute("SELECT numero, capacidad FROM mesas WHERE numero != 99;")
            mesas_db = cursor.fetchall()

        # Obtener mesas ocupadas en ese momento (basado en pedidos activos)
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT mesa_numero
                FROM pedidos
                WHERE estado IN ('Tomando pedido', 'Pendiente', 'En preparacion', 'Listo', 'Entregado')
                AND mesa_numero != 99;
            """)
            ocupadas_db = set(row['mesa_numero'] for row in cursor.fetchall())

        # Obtener mesas reservadas en ese momento
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT mesa_numero
                FROM reservas
                WHERE %s BETWEEN fecha_hora_inicio AND COALESCE(fecha_hora_fin, fecha_hora_inicio + INTERVAL '1 hour');
                -- Asumimos una duración de 1 hora si no se especifica fin
            """, (fecha_hora_obj,))
            reservadas_db = set(row['mesa_numero'] for row in cursor.fetchall())

        mesas_disponibles = []
        for mesa in mesas_db:
            if mesa['numero'] not in ocupadas_db and mesa['numero'] not in reservadas_db:
                mesas_disponibles.append({
                    "numero": mesa['numero'],
                    "capacidad": mesa['capacidad']
                })

        return mesas_disponibles

    except Exception as e:
        print(f"Error en obtener_mesas_disponibles_para_fecha_hora: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor al consultar disponibilidad.")
    

class ReservaCreate(BaseModel):
    mesa_numero: int
    cliente_id: int
    fecha_hora_inicio: str  # "YYYY-MM-DD HH:MM:SS"
    fecha_hora_fin: Optional[str] = None # "YYYY-MM-DD HH:MM:SS"

class ReservaUpdate(BaseModel):
    mesa_numero: Optional[int] = None
    cliente_id: Optional[int] = None
    fecha_hora_inicio: Optional[str] = None # "YYYY-MM-DD HH:MM:SS"
    fecha_hora_fin: Optional[str] = None # "YYYY-MM-DD HH:MM:SS"

@app.get("/reservas/")
def obtener_reservas(
    fecha: Optional[str] = Query(None, description="Fecha en formato YYYY-MM-DD para filtrar"),
    conn = Depends(get_db)
):
    """
    Obtiene todas las reservas o filtra por fecha.
    """
    try:
        query = """
            SELECT r.id, r.mesa_numero, r.cliente_id, c.nombre as cliente_nombre, r.fecha_hora_inicio, r.fecha_hora_fin
            FROM reservas r
            JOIN clientes c ON r.cliente_id = c.id
        """
        params = []
        if fecha:
            query += " WHERE DATE(r.fecha_hora_inicio) = %s"
            params.append(fecha)

        query += " ORDER BY r.fecha_hora_inicio;"

        with conn.cursor() as cursor:
            cursor.execute(query, params)
            reservas_db = cursor.fetchall()

        reservas = []
        for res in reservas_db:
            reservas.append({
                "id": res['id'],
                "mesa_numero": res['mesa_numero'],
                "cliente_id": res['cliente_id'],
                "cliente_nombre": res['cliente_nombre'],
                "fecha_hora_inicio": str(res['fecha_hora_inicio']),
                "fecha_hora_fin": str(res['fecha_hora_fin']) if res['fecha_hora_fin'] else None
            })

        return reservas

    except Exception as e:
        print(f"Error en obtener_reservas: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor al obtener reservas.")


@app.post("/reservas/", status_code=201)
def crear_reserva_simplificada(reserva: ReservaCreate, conn = Depends(get_db)):
    """
    Crea una nueva reserva. Versión simplificada sin verificación de conflictos.
    """
    try:
        # Asumimos que cliente_id y mesa_numero son válidos (verificados por Pydantic)
        # Asumimos que fecha_hora_inicio y fecha_hora_fin tienen el formato correcto (verificado por Pydantic o antes)
        # No verificamos conflictos de horarios por ahora

        # Calcular fecha_hora_fin si es None
        fecha_inicio_obj = datetime.fromisoformat(reserva.fecha_hora_inicio.replace(" ", "T"))
        if reserva.fecha_hora_fin:
            fecha_fin_obj = datetime.fromisoformat(reserva.fecha_hora_fin.replace(" ", "T"))
        else:
            fecha_fin_obj = fecha_inicio_obj + timedelta(hours=1) # Asumir 1 hora si no se da fin

        with conn.cursor() as cursor:
            # Insertar la reserva directamente
            # Usamos placeholders %s para evitar inyección SQL
            cursor.execute("""
                INSERT INTO reservas (mesa_numero, cliente_id, fecha_hora_inicio, fecha_hora_fin)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
            """, (reserva.mesa_numero, reserva.cliente_id, fecha_inicio_obj, fecha_fin_obj))
            reserva_id = cursor.fetchone()['id']
        conn.commit() # Confirmar la transacción

        # Opcional: Obtener y devolver la reserva creada
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT r.id, r.mesa_numero, r.cliente_id, c.nombre as cliente_nombre, r.fecha_hora_inicio, r.fecha_hora_fin
                FROM reservas r
                JOIN clientes c ON r.cliente_id = c.id
                WHERE r.id = %s;
            """, (reserva_id,))
            nueva_reserva_db = cursor.fetchone()

        if not nueva_reserva_db:
            # Esto es raro, pero por si acaso
            raise HTTPException(status_code=404, detail="Reserva no encontrada después de crearla.")

        return {
            "id": nueva_reserva_db['id'],
            "mesa_numero": nueva_reserva_db['mesa_numero'],
            "cliente_id": nueva_reserva_db['cliente_id'],
            "cliente_nombre": nueva_reserva_db['cliente_nombre'],
            "fecha_hora_inicio": str(nueva_reserva_db['fecha_hora_inicio']),
            "fecha_hora_fin": str(nueva_reserva_db['fecha_hora_fin']) if nueva_reserva_db['fecha_hora_fin'] else None
        }

    except ValueError as ve:
        # Captura errores de formato de fecha/hora si fromisoformat falla
        print(f"Error de formato de fecha/hora en el backend: {ve}")
        raise HTTPException(status_code=400, detail=f"Formato de fecha/hora inválido: {ve}")
    except HTTPException:
        # Re-raise HTTP exceptions (como 400, 404)
        raise
    except Exception as e:
        # Captura cualquier otro error inesperado
        print(f"Error interno en crear_reserva_simplificada: {e}")
        import traceback
        traceback.print_exc() # Imprime el traceback completo
        conn.rollback() # Revertir la transacción en caso de error inesperado
        raise HTTPException(status_code=500, detail="Error interno del servidor al crear la reserva.")


@app.delete("/reservas/{reserva_id}")
def eliminar_reserva(reserva_id: int, conn = Depends(get_db)):
    """
    Elimina una reserva existente por su ID.
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM reservas WHERE id = %s RETURNING id;", (reserva_id,))
            eliminado = cursor.fetchone()
            if not eliminado:
                raise HTTPException(status_code=404, detail="Reserva no encontrada")

        conn.commit()
        return {"status": "ok", "message": "Reserva eliminada"}

    except HTTPException:
        # Re-raise HTTP exceptions (como 404)
        raise
    except Exception as e:
        print(f"Error en eliminar_reserva: {e}")
        conn.rollback() # Revertir la transacción en caso de error
        raise HTTPException(status_code=500, detail="Error interno del servidor al eliminar la reserva.")
    
# --- NUEVO ENDPOINT CORREGIDO: Ventas por Hora ---
@app.get("/reportes/ventas_por_hora")
def obtener_ventas_por_hora(
    fecha: str = Query(..., description="Fecha en formato YYYY-MM-DD para filtrar ventas por hora"),
    conn: psycopg2.extensions.connection = Depends(get_db)
):
    """
    Obtiene el total de ventas por hora para una fecha específica.
    Args:
        fecha (str): Fecha en formato 'YYYY-MM-DD'.
        conn: Conexión a la base de datos.
    Returns:
        Dict[str, float]: Diccionario con hora (00-23) como clave y total de ventas como valor.
    """
    try:
        # Asegurar que la fecha tiene el formato correcto
        datetime.strptime(fecha, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD.")

    try:
        with conn.cursor() as cursor:
            # Consultar pedidos completados (Pagado o Entregado) para la fecha dada
            # Extraer la hora de la fecha_hora y sumar el total de cada pedido
            # Seleccionar el nombre y el precio de cada ítem en el array JSONB 'items'
            cursor.execute("""
                SELECT EXTRACT(HOUR FROM fecha_hora) AS hora, SUM(item_data.precio) AS total_venta
                FROM pedidos,
                     jsonb_to_recordset(pedidos.items) AS item_data(nombre TEXT, precio REAL, tipo TEXT, cantidad INTEGER)
                WHERE DATE(fecha_hora) = %s
                AND estado IN ('Entregado', 'Pagado') -- Ajustar según tu definición de venta completada
                GROUP BY EXTRACT(HOUR FROM fecha_hora)
                ORDER BY hora;
            """, (fecha,))
            
            resultados_db = cursor.fetchall()

        # Inicializar un diccionario con todas las horas del día a 0.0
        ventas_por_hora = {f"{h:02d}": 0.0 for h in range(24)} # Usar f-string para asegurar formato '00', '01', ..., '23'

        # Llenar el diccionario con los resultados de la base de datos
        for row in resultados_db:
            # Asegurar que hora es un entero y total_venta es un número
            hora_int = int(row['hora'])
            total_venta_db = row['total_venta']
            # Si total_venta_db es None (por ejemplo, si no hay items), usar 0.0
            total_venta = float(total_venta_db) if total_venta_db is not None else 0.0
            hora_str = f"{hora_int:02d}" # Convertir a string con formato '00', '01', ..., '23'
            ventas_por_hora[hora_str] = total_venta

        return ventas_por_hora
    except Exception as e:
        # Capturar cualquier error interno del servidor y loguearlo
        print(f"Error interno en obtener_ventas_por_hora: {e}")
        import traceback
        traceback.print_exc() # Imprime el traceback completo
        raise HTTPException(status_code=500, detail=f"Error interno del servidor al calcular ventas por hora: {str(e)}")
# --- FIN NUEVO ENDPOINT CORREGIDO ---

# --- NUEVO ENDPOINT: Eficiencia de Cocina ---
@app.get("/reportes/eficiencia_cocina")
def get_eficiencia_cocina(tipo: str, start_date: str, end_date: str, conn = Depends(get_db)):
    """
    Obtiene estadísticas de eficiencia de cocina para un rango de fechas.
    """
    with conn.cursor() as cursor:
        # Consulta para obtener pedidos que tengan hora_inicio_cocina y hora_fin_cocina
        # y que estén dentro del rango de fechas.
        # Filtrar por estado que indica que cocina terminó (Listo, Entregado, Pagado)
        # Suponiendo que hora_fin_cocina se registra al pasar a 'Listo'.
        query = """
            SELECT
                id,
                hora_inicio_cocina,
                hora_fin_cocina,
                (EXTRACT(EPOCH FROM (hora_fin_cocina - hora_inicio_cocina)) / 60.0) AS tiempo_cocina_minutos
            FROM pedidos
            WHERE
                hora_inicio_cocina IS NOT NULL
                AND hora_fin_cocina IS NOT NULL
                AND hora_inicio_cocina >= %s
                AND hora_fin_cocina <= %s
                AND estado IN ('Listo', 'Entregado', 'Pagado') -- Ajustar según sea necesario
            ORDER BY hora_fin_cocina; -- O por id, o por hora_inicio_cocina
        """
        cursor.execute(query, (start_date, end_date))
        pedidos_db = cursor.fetchall()

        if not pedidos_db:
            return {"promedio_minutos": 0, "detalle_pedidos": []}

        tiempos = [row['tiempo_cocina_minutos'] for row in pedidos_db]
        promedio = sum(tiempos) / len(tiempos)

        detalle = [
            {
                "id": row['id'],
                "tiempo": row['tiempo_cocina_minutos']
            }
            for row in pedidos_db
        ]

        return {
            "promedio_minutos": promedio,
            "detalle_pedidos": detalle
        }
# --- FIN NUEVO ENDPOINT ---
