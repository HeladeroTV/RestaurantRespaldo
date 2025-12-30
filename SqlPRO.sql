-- === SCRIPT SQL PARA CREAR BASE DE DATOS RESTIA COMPLETA ===
-- Este script crea la base de datos, tablas, índices, triggers y datos iniciales
-- para el sistema RestIA con funcionalidades avanzadas de reportes y alertas personalizadas.

-- 1. CREAR LA BASE DE DATOS (ejecutar como superusuario o en base 'postgres')
-- DESCOMENTA LA SIGUIENTE LÍNEA SI DESEAS CREAR LA BASE DE DATOS DESDE CERO
-- CREATE DATABASE restaurant_db;

-- 2. CONECTARSE A LA BASE DE DATOS 'restaurant_db' ANTES DE EJECUTAR EL RESTO DEL SCRIPT
-- \c restaurant_db; -- (Comando para psql)

-- 3. CREAR TABLAS (en orden correcto para respetar dependencias)

-- Tabla: clientes
-- Almacena información de los clientes registrados.
CREATE TABLE IF NOT EXISTS clientes (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    domicilio TEXT,
    celular VARCHAR(20),
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: mesas
-- Define las mesas físicas del restaurante y la mesa virtual (99).
CREATE TABLE IF NOT EXISTS mesas (
    id SERIAL PRIMARY KEY,
    numero INTEGER NOT NULL UNIQUE, -- Ej: 1, 2, ..., 6, 99
    capacidad INTEGER NOT NULL DEFAULT 1 CHECK (capacidad > 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insertar mesas por defecto (1 a 6) y la mesa virtual (99)
INSERT INTO mesas (numero, capacidad) VALUES
(1, 2), (2, 2), (3, 4), (4, 4), (5, 6), (6, 6), (99, 100) -- Mesa virtual
ON CONFLICT (numero) DO NOTHING; -- Evita errores si ya existen

-- Tabla: menu
-- Define los ítems del menú.
CREATE TABLE IF NOT EXISTS menu (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL UNIQUE,
    precio DECIMAL(10, 2) NOT NULL CHECK (precio >= 0),
    tipo VARCHAR(100), -- Ej: Entrante, Plato Principal, Bebida, Postre
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: inventario
-- Almacena los ingredientes y su stock.
CREATE TABLE IF NOT EXISTS inventario (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL UNIQUE,
    descripcion TEXT,
    cantidad_disponible DECIMAL(10, 2) NOT NULL DEFAULT 0 CHECK (cantidad_disponible >= 0),
    unidad_medida VARCHAR(50) DEFAULT 'unidad', -- Ej: unidad, kg, g, lt, ml
    cantidad_minima DECIMAL(10, 2) NOT NULL DEFAULT 0 CHECK (cantidad_minima >= 0), -- Nivel mínimo antes de alertar
    -- *** NUEVO CAMPO PARA ALERTAS PERSONALIZADAS ***
    cantidad_minima_alerta DECIMAL(10, 2) NOT NULL DEFAULT 5.0 CHECK (cantidad_minima_alerta >= 0),
    -- *** FIN NUEVO CAMPO ***
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: recetas
-- Define las recetas para cada plato del menú.
CREATE TABLE IF NOT EXISTS recetas (
    id SERIAL PRIMARY KEY,
    nombre_plato VARCHAR(255) NOT NULL UNIQUE, -- Debe coincidir con un nombre en 'menu'
    descripcion TEXT,
    instrucciones TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (nombre_plato) REFERENCES menu(nombre) ON DELETE CASCADE -- Si se elimina el plato, se elimina la receta
);

-- Tabla: ingredientes_recetas
-- Relación muchos a muchos entre recetas e ingredientes del inventario.
CREATE TABLE IF NOT EXISTS ingredientes_recetas (
    id SERIAL PRIMARY KEY,
    receta_id INTEGER NOT NULL,
    ingrediente_id INTEGER NOT NULL,
    cantidad_necesaria DECIMAL(10, 2) NOT NULL CHECK (cantidad_necesaria > 0),
    unidad_medida_necesaria VARCHAR(50) NOT NULL, -- Unidad en la que se necesita según la receta
    FOREIGN KEY (receta_id) REFERENCES recetas(id) ON DELETE CASCADE, -- Si se elimina la receta, se eliminan los ingredientes
    FOREIGN KEY (ingrediente_id) REFERENCES inventario(id) ON DELETE RESTRICT, -- Impide eliminar ingrediente si está en una receta
    UNIQUE (receta_id, ingrediente_id) -- No se puede repetir un ingrediente en la misma receta
);

-- Tabla: pedidos
-- Almacena los pedidos realizados.
CREATE TABLE IF NOT EXISTS pedidos (
    id SERIAL PRIMARY KEY,
    mesa_numero INTEGER NOT NULL,
    cliente_id INTEGER, -- Puede ser NULL si no es cliente registrado
    estado VARCHAR(50) NOT NULL DEFAULT 'Tomando pedido' CHECK (estado IN ('Tomando pedido', 'Pendiente', 'En preparacion', 'Listo', 'Entregado', 'Pagado')),
    fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    items JSONB NOT NULL DEFAULT '[]'::jsonb, -- Almacena los ítems del pedido como JSONB
    numero_app INTEGER, -- Para pedidos de la app virtual (mesa 99)
    notas TEXT DEFAULT '', -- Notas del cliente para el pedido
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- *** CRUCIAL PARA EFICIENCIA COCINA ***
    -- *** CAMPOS PARA EFICIENCIA COCINA ***
    hora_inicio_cocina TIMESTAMP NULL, -- Hora en que empieza a prepararse
    hora_fin_cocina TIMESTAMP NULL, -- Hora en que termina de prepararse
    -- *** FIN CAMPOS ***
    FOREIGN KEY (mesa_numero) REFERENCES mesas(numero) ON DELETE SET NULL, -- Si se borra la mesa, el pedido queda sin mesa
    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE SET NULL -- Si se borra el cliente, el pedido queda sin cliente
);

-- Tabla: reservas
-- Almacena las reservas de mesas.
CREATE TABLE IF NOT EXISTS reservas (
    id SERIAL PRIMARY KEY,
    mesa_numero INTEGER NOT NULL,
    cliente_id INTEGER NOT NULL,
    fecha_hora_inicio TIMESTAMP NOT NULL,
    fecha_hora_fin TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (mesa_numero) REFERENCES mesas(numero) ON DELETE CASCADE, -- Si se elimina la mesa, se elimina la reserva
    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE -- Si se elimina el cliente, se elimina la reserva
);

-- Tabla: configuraciones (almacenada localmente en JSON, pero definida aquí por si acaso)
-- Esta tabla se usa en configuraciones_backend.py.
CREATE TABLE IF NOT EXISTS configuraciones (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL UNIQUE,
    descripcion TEXT,
    ingredientes JSONB NOT NULL DEFAULT '[]'::jsonb, -- Almacena la lista de ingredientes como JSONB
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Índices (para mejorar rendimiento en consultas frecuentes)

-- Índice en pedidos por estado y fecha_hora (para reportes y vistas activas)
CREATE INDEX IF NOT EXISTS idx_pedidos_estado_fecha ON pedidos (estado, fecha_hora DESC);

-- Índice en pedidos por mesa_numero y estado (para vistas de mesas activas)
CREATE INDEX IF NOT EXISTS idx_pedidos_mesa_estado_activos ON pedidos (mesa_numero, estado) WHERE estado IN ('Pendiente', 'En preparacion', 'Listo');

-- Índice en pedidos por fecha_hora (para reportes generales)
CREATE INDEX IF NOT EXISTS idx_pedidos_fecha ON pedidos (fecha_hora);

-- Índice en pedidos por mesa_numero (para vistas de mesas)
CREATE INDEX IF NOT EXISTS idx_pedidos_mesa ON pedidos (mesa_numero);

-- Índice en inventario por cantidad_disponible y cantidad_minima_alerta (para alertas de stock)
CREATE INDEX IF NOT EXISTS idx_inventario_stock ON inventario (cantidad_disponible, cantidad_minima_alerta);

-- Índice en reservas por fecha_hora_inicio (para vistas de reservas)
CREATE INDEX IF NOT EXISTS idx_reservas_fecha_inicio ON reservas (fecha_hora_inicio);

-- Índice en reservas por fecha_hora_inicio y fecha_hora_fin (para disponibilidad de mesas)
CREATE INDEX IF NOT EXISTS idx_reservas_fecha_hora ON reservas (fecha_hora_inicio, fecha_hora_fin);

-- Índice en clientes por nombre (para búsqueda rápida)
CREATE INDEX IF NOT EXISTS idx_clientes_nombre ON clientes (nombre);

-- Índice en menu por tipo (para vistas de cocina)
CREATE INDEX IF NOT EXISTS idx_menu_tipo ON menu (tipo);

-- 5. Triggers para actualizar `updated_at` y `fecha_actualizacion` automáticamente (mejora integridad y facilita reportes)

-- Trigger para actualizar `updated_at` en `pedidos` antes de cada UPDATE
CREATE OR REPLACE FUNCTION actualizar_fecha_pedido()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_actualizar_fecha_pedido
    BEFORE UPDATE ON pedidos
    FOR EACH ROW
    EXECUTE FUNCTION actualizar_fecha_pedido();

-- Trigger para actualizar `fecha_actualizacion` en `inventario` antes de cada UPDATE
CREATE OR REPLACE FUNCTION actualizar_fecha_inventario()
RETURNS TRIGGER AS $$
BEGIN
    NEW.fecha_actualizacion = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_actualizar_fecha_inventario
    BEFORE UPDATE ON inventario
    FOR EACH ROW
    EXECUTE FUNCTION actualizar_fecha_inventario();

-- Trigger para actualizar `fecha_actualizacion` en `recetas` antes de cada UPDATE
CREATE OR REPLACE FUNCTION actualizar_fecha_receta()
RETURNS TRIGGER AS $$
BEGIN
    NEW.fecha_actualizacion = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_actualizar_fecha_receta
    BEFORE UPDATE ON recetas
    FOR EACH ROW
    EXECUTE FUNCTION actualizar_fecha_receta();

-- 6. Insertar datos de ejemplo para probar

-- Clientes de ejemplo
INSERT INTO clientes (nombre, domicilio, celular) VALUES
('Cliente de Prueba 1', 'Calle Falsa 123', '123456789'),
('Cliente de Prueba 2', 'Avenida Siempre Viva 742', '987654321')
ON CONFLICT (id) DO NOTHING;

-- Ítems de menú de ejemplo (tu menú original)
INSERT INTO menu (nombre, precio, tipo) VALUES
-- Entradas
('Empanada Kunai', 70.00, 'Entradas'),
('Dedos de queso (5pz)', 75.00, 'Entradas'),
('Chile Relleno', 60.00, 'Entradas'),
('Caribe Poppers', 130.00, 'Entradas'),
('Brocheta', 50.00, 'Entradas'),
('Rollos Primavera (2pz)', 100.00, 'Entradas'),
-- Platillos
('Camarones roca', 160.00, 'Platillos'),
('Teriyaki', 130.00, 'Platillos'),
('Bonneles (300gr)', 150.00, 'Platillos'),
-- Arroces
('Yakimeshi Especial', 150.00, 'Arroces'),
('Yakimeshi Kunai', 140.00, 'Arroces'),
('Yakimeshi Golden', 145.00, 'Arroces'),
('Yakimeshi Horneado', 145.00, 'Arroces'),
('Gohan Mixto', 125.00, 'Arroces'),
('Gohan Crispy', 125.00, 'Arroces'),
('Gohan Chicken', 120.00, 'Arroces'),
('Kunai Burguer', 140.00, 'Arroces'),
('Bomba', 105.00, 'Arroces'),
('Bomba Especial', 135.00, 'Arroces'),
-- Naturales
('Guamuchilito', 110.00, 'Naturales'),
('Avocado', 125.00, 'Naturales'),
('Grenudo Roll', 135.00, 'Naturales'),
('Granja Roll', 115.00, 'Naturales'),
('California Roll', 100.00, 'Naturales'),
('California Especial', 130.00, 'Naturales'),
('Arcoíris', 120.00, 'Naturales'),
('Tuna Roll', 130.00, 'Naturales'),
('Kusanagi', 130.00, 'Naturales'),
('Kanisweet', 120.00, 'Naturales'),
-- Empanizados
('Mar y Tierra', 95.00, 'Empanizados'),
('Tres Quesos', 100.00, 'Empanizados'),
('Cordon Blue', 105.00, 'Empanizados'),
('Roka Roll', 135.00, 'Empanizados'),
('Camarón Bacon', 110.00, 'Empanizados'),
('Cielo, mar y tierra', 110.00, 'Empanizados'),
('Konan Roll', 130.00, 'Empanizados'),
('Pain Roll', 115.00, 'Empanizados'),
('Sasori Roll', 125.00, 'Empanizados'),
('Chikin', 130.00, 'Empanizados'),
('Caribe Roll', 115.00, 'Empanizados'),
('Chon', 120.00, 'Empanizados'),
-- Gratinados
('Kunai Especial', 150.00, 'Gratinados'),
('Chuma Roll', 145.00, 'Gratinados'),
('Choche Roll', 140.00, 'Gratinados'),
('Milán Roll', 135.00, 'Gratinados'),
('Chio Roll', 145.00, 'Gratinados'),
('Prime', 140.00, 'Gratinados'),
('Ninja Roll', 135.00, 'Gratinados'),
('Serranito', 135.00, 'Gratinados'),
('Sanji', 145.00, 'Gratinados'),
('Monkey Roll', 135.00, 'Gratinados'),
-- Kunai Kids
('Baby Roll (8pz)', 60.00, 'Kunai Kids'),
('Chicken Sweet (7pz)', 60.00, 'Kunai Kids'),
('Chesse Puffs (10pz)', 55.00, 'Kunai Kids'),
-- Bebidas
('Te refil', 35.00, 'Bebidas'),
('Te de litro', 35.00, 'Bebidas'),
('Coca-cola', 35.00, 'Bebidas'),
('Agua natural', 20.00, 'Bebidas'),
('Agua mineral', 35.00, 'Bebidas'),
-- Extras
('Camaron', 20.00, 'Extras'),
('Res', 15.00, 'Extras'),
('Pollo', 15.00, 'Extras'),
('Tocino', 15.00, 'Extras'),
('Gratinado', 15.00, 'Extras'),
('Aguacate', 25.00, 'Extras'),
('Empanizado', 15.00, 'Extras'),
('Philadelphia', 10.00, 'Extras'),
('Tampico', 25.00, 'Extras'),
('Siracha', 10.00, 'Extras'),
('Soya', 10.00, 'Extras')
ON CONFLICT (id) DO NOTHING;

-- Ingredientes de inventario de ejemplo
INSERT INTO inventario (nombre, descripcion, cantidad_disponible, unidad_medida, cantidad_minima, cantidad_minima_alerta) VALUES
('Pollo', 'Pechuga de pollo fresco', 20.0, 'kg', 2.0, 5.0),
('Arroz', 'Arroz blanco grano largo', 10.0, 'kg', 1.0, 2.0),
('Salsa de Soja', 'Salsa de soja light', 5.0, 'lt', 0.5, 1.0),
('Camaron', 'Camaron crudo', 15.0, 'kg', 1.0, 3.0),
('Verduras Mixtas', 'Mezcla de verduras congeladas', 8.0, 'kg', 1.0, 2.0)
ON CONFLICT (id) DO NOTHING;

-- Recetas de ejemplo (asociadas a ítems del menú)
-- Suponiendo que 'Yakimeshi Especial' tiene id 10 en la tabla menu
INSERT INTO recetas (nombre_plato, descripcion, instrucciones) VALUES
('Yakimeshi Especial', 'Yakimeshi con camarones y verduras', 'Saltear arroz con verduras, agregar camarones y salsa.')
ON CONFLICT (id) DO NOTHING;

-- Asociar ingredientes a la receta 'Yakimeshi Especial' (suponiendo receta_id = 1, Arroz id = 2, Camaron id = 4, Verduras id = 5)
-- Ajusta los IDs si no coinciden con tu inserción real
-- INSERT INTO ingredientes_recetas (receta_id, ingrediente_id, cantidad_necesaria, unidad_medida_necesaria) VALUES
-- (1, 2, 0.15, 'kg'), -- 150g de Arroz
-- (1, 4, 0.05, 'kg'), -- 50g de Camaron
-- (1, 5, 0.05, 'kg')  -- 50g de Verduras Mixtas
-- ON CONFLICT (id) DO NOTHING;

-- Insertar una configuración de ejemplo
-- INSERT INTO configuraciones (nombre, descripcion, ingredientes) VALUES
-- ('Stock Basico', 'Ingredientes iniciales comunes', '[{"nombre": "Pollo", "cantidad": 10, "unidad": "kg"}, {"nombre": "Arroz", "cantidad": 5, "unidad": "kg"}]')
-- ON CONFLICT (id) DO NOTHING;

-- Fin del script