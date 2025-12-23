-- crear_base_datos_restaurant.sql
-- Script para crear la base de datos completa del sistema de restaurante.

-- Conéctate a PostgreSQL como superusuario (por ejemplo, 'postgres')
-- y ejecuta este script para crear la base de datos y sus tablas.

-- 1. CREAR LA BASE DE DATOS (si no existe)
-- Opcional: Eliminarla si ya existe para reiniciar completamente (¡cuidado con los datos existentes!)
-- DROP DATABASE IF EXISTS restaurant_db;

CREATE DATABASE restaurant_db;

-- Conéctate a la base de datos recién creada antes de ejecutar el resto del script.
-- En psql, puedes usar: \c restaurant_db
-- Este script asume que ya estás conectado a 'restaurant_db'.

-- 2. CREAR LAS TABLAS (dentro de restaurant_db)

-- 2.1. TABLA: mesas
-- Almacena la información de las mesas físicas y la mesa virtual.
CREATE TABLE IF NOT EXISTS mesas (
    id SERIAL PRIMARY KEY,
    numero INTEGER NOT NULL UNIQUE, -- Ej: 1, 2, ..., 6, 99
    capacidad INTEGER NOT NULL DEFAULT 1, -- Número de comensales
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insertar mesas iniciales (físicas y virtual) si no existen
INSERT INTO mesas (numero, capacidad) VALUES
(1, 2), (2, 2), (3, 4), (4, 4), (5, 6), (6, 6), (99, 100) -- Mesa virtual
ON CONFLICT (numero) DO NOTHING;

-- 2.2. TABLA: menu
-- Almacena los items disponibles en el menú.
CREATE TABLE IF NOT EXISTS menu (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    precio REAL NOT NULL,
    tipo TEXT NOT NULL -- Ej: 'Entradas', 'Platos Fuertes', 'Postres', 'Bebidas'
);

-- Insertar items de ejemplo en el menú
INSERT INTO menu (nombre, precio, tipo) VALUES
('Empanada Kunai', 70.00, 'Entradas'),
('Camarones roca', 160.00, 'Platillos'),
('Yakimeshi Especial', 150.00, 'Arroces'),
('Soda', 30.00, 'Bebidas'),
('Cerveza', 45.00, 'Bebidas')
ON CONFLICT (nombre) DO NOTHING; -- Evita errores si ya existen

-- 2.3. TABLA: clientes
-- Almacena la información de los clientes registrados.
CREATE TABLE IF NOT EXISTS clientes (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    domicilio TEXT,
    celular TEXT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insertar clientes de ejemplo
INSERT INTO clientes (nombre, domicilio, celular) VALUES
('Cliente Ejemplo 1', 'Direccion Ejemplo 1', '1111111111'),
('Cliente Ejemplo 2', 'Direccion Ejemplo 2', '2222222222')
ON CONFLICT (id) DO NOTHING; -- Asumiendo ID autoincremental, ON CONFLICT no aplica directamente aquí, pero puedes usar DO NOTHING si insertas con ID fijo

-- 2.4. TABLA: pedidos
-- Almacena cada pedido realizado.
CREATE TABLE IF NOT EXISTS pedidos (
    id SERIAL PRIMARY KEY,
    mesa_numero INTEGER NOT NULL,
    cliente_id INTEGER, -- Puede ser NULL si no es cliente registrado o es pedido digital
    estado TEXT NOT NULL DEFAULT 'Tomando pedido', -- 'Tomando pedido', 'Pendiente', 'En preparacion', 'Listo', 'Entregado', 'Pagado'
    fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    items JSONB NOT NULL DEFAULT '[]'::jsonb, -- Almacena el array de ítems como JSON
    numero_app INTEGER, -- Para identificar pedidos de la app digital (asignado cuando mesa_numero = 99)
    notas TEXT DEFAULT '', -- Notas del pedido
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Útil para rastrear modificaciones
    -- --- AÑADIR COLUMNAS PARA EFICIENCIA DE COCINA ---
    hora_inicio_cocina TIMESTAMP NULL,
    hora_fin_cocina TIMESTAMP NULL
    -- --- FIN AÑADIR COLUMNAS ---
    -- Claves foráneas
    FOREIGN KEY (mesa_numero) REFERENCES mesas(numero) ON DELETE SET NULL, -- Si se borra la mesa, el pedido queda sin mesa
    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE SET NULL -- Si se borra el cliente, el pedido queda sin cliente
);

-- Índices para optimizar consultas comunes
CREATE INDEX IF NOT EXISTS idx_pedidos_estado_fecha ON pedidos (estado, fecha_hora DESC);
CREATE INDEX IF NOT EXISTS idx_pedidos_mesa_estado_activos ON pedidos (mesa_numero, estado) WHERE estado IN ('Pendiente', 'En preparacion', 'Listo');

-- 2.5. TABLA: inventario
-- Almacena los items del inventario.
CREATE TABLE IF NOT EXISTS inventario (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE, -- Nombre del ingrediente o producto
    descripcion TEXT,
    cantidad_disponible REAL NOT NULL DEFAULT 0,
    unidad_medida TEXT NOT NULL, -- Ej: 'kg', 'g', 'lt', 'ml', 'unidades', 'docenas'
    -- --- AÑADIR COLUMNA PARA UMBRAL PERSONALIZADO ---
    cantidad_minima_alerta REAL DEFAULT 5.0 -- Nivel mínimo antes de alertar
    -- --- FIN AÑADIR COLUMNA ---
    -- cantidad_minima REAL DEFAULT 0, -- Nivel mínimo antes de alertar (Anterior)
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insertar inventario de ejemplo
INSERT INTO inventario (nombre, descripcion, cantidad_disponible, unidad_medida, cantidad_minima_alerta) VALUES
('Pollo', 'Pechuga de pollo fresco', 20.0, 'kg', 5.0),
('Arroz', 'Arroz blanco grano largo', 10.0, 'kg', 2.0),
('Salsa de Soja', 'Salsa de soja light', 5.0, 'lt', 1.0),
('Camarones', 'Camarones frescos', 15.0, 'kg', 3.0)
ON CONFLICT (nombre) DO NOTHING;

-- 2.6. TABLA: recetas
-- Almacena las recetas de los platos del menú.
CREATE TABLE IF NOT EXISTS recetas (
    id SERIAL PRIMARY KEY,
    nombre_plato TEXT NOT NULL UNIQUE, -- Nombre del plato del menú (debe coincidir con menu.nombre)
    descripcion TEXT,                 -- Descripción opcional de la receta
    instrucciones TEXT,               -- Pasos para preparar la receta
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (nombre_plato) REFERENCES menu(nombre) ON DELETE CASCADE -- Si se borra el plato, se borra la receta
);

-- 2.7. TABLA: ingredientes_recetas
-- Relaciona los ingredientes (del inventario) con las recetas y la cantidad necesaria.
CREATE TABLE IF NOT EXISTS ingredientes_recetas (
    id SERIAL PRIMARY KEY,
    receta_id INTEGER NOT NULL,
    ingrediente_id INTEGER NOT NULL,
    cantidad_necesaria REAL NOT NULL, -- Cantidad del ingrediente necesaria para una unidad del plato
    unidad_medida_necesaria TEXT NOT NULL, -- Unidad de medida necesaria (ej: 'g', 'kg', 'ml', 'unidad')
    FOREIGN KEY (receta_id) REFERENCES recetas(id) ON DELETE CASCADE, -- Si se borra la receta, se borra el ingrediente de la receta
    FOREIGN KEY (ingrediente_id) REFERENCES inventario(id) ON DELETE RESTRICT -- Si un ingrediente se usa en una receta, no se puede borrar del inventario
);

-- Opcional: Crear un índice para optimizar la consulta de ingredientes por receta
CREATE INDEX IF NOT EXISTS idx_ingredientes_recetas_receta_id ON ingredientes_recetas (receta_id);

-- 2.8. TABLA: configuraciones
-- Almacena configuraciones generales del sistema, específicamente para listas de ingredientes.
CREATE TABLE IF NOT EXISTS configuraciones (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,          -- Nombre de la configuración (ej: "Stock Inicial", "Promo Semanal")
    descripcion TEXT,                     -- Descripción de la configuración
    ingredientes JSONB NOT NULL DEFAULT '[]'::jsonb  -- Array de ingredientes como JSON: [{"nombre": "...", "cantidad": ..., "unidad": "..."}, ...]
);

-- Opcional: Insertar una configuración de ejemplo
INSERT INTO configuraciones (nombre, descripcion, ingredientes) VALUES
('Stock Basico', 'Ingredientes iniciales comunes', '[{"nombre": "Pollo", "cantidad": 10, "unidad": "kg"}, {"nombre": "Arroz", "cantidad": 5, "unidad": "kg"}]')
ON CONFLICT (nombre) DO NOTHING;

-- 2.9. TABLA: reservas (si la implementaste)
-- Almacena las reservas de mesas.
CREATE TABLE IF NOT EXISTS reservas (
    id SERIAL PRIMARY KEY,
    mesa_numero INTEGER NOT NULL,
    cliente_id INTEGER NOT NULL,
    fecha_hora_inicio TIMESTAMP NOT NULL,
    fecha_hora_fin TIMESTAMP, -- Opcional
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (mesa_numero) REFERENCES mesas(numero) ON DELETE CASCADE, -- Si se borra la mesa, se borra la reserva
    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE  -- Si se borra el cliente, se borra la reserva
);

-- Índice para optimizar la consulta de mesas disponibles
CREATE INDEX IF NOT EXISTS idx_reservas_fecha_hora ON reservas (fecha_hora_inicio, fecha_hora_fin);

-- 3. FINALIZAR
-- El script termina aquí. La base de datos y todas las tablas están creadas.
-- echo "Base de datos 'restaurant_db' y tablas creadas exitosamente.";