PRAGMA foreign_keys = ON;

CREATE TABLE roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome VARCHAR(40) NOT NULL UNIQUE,
    descrizione VARCHAR(255),
    data_creazione DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_aggiornamento DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_roles_nome ON roles (nome);

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(60) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    ruolo_id INTEGER NOT NULL,
    attivo BOOLEAN NOT NULL DEFAULT 1,
    data_creazione DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_aggiornamento DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ruolo_id) REFERENCES roles(id)
);
CREATE INDEX ix_users_username ON users (username);
CREATE UNIQUE INDEX uq_users_username_lower ON users (lower(username));
CREATE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_ruolo_id ON users (ruolo_id);
CREATE INDEX ix_users_attivo ON users (attivo);

CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome VARCHAR(100) NOT NULL UNIQUE,
    descrizione VARCHAR(255),
    data_creazione DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_aggiornamento DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_categories_nome ON categories (nome);

CREATE TABLE brands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome VARCHAR(100) NOT NULL UNIQUE,
    descrizione VARCHAR(255),
    data_creazione DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_aggiornamento DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_brands_nome ON brands (nome);

CREATE TABLE compatibilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome VARCHAR(120) NOT NULL UNIQUE,
    descrizione VARCHAR(255),
    data_creazione DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_aggiornamento DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_compatibilities_nome ON compatibilities (nome);

CREATE TABLE vat_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome VARCHAR(80) NOT NULL UNIQUE,
    aliquota NUMERIC(5,2) NOT NULL DEFAULT 22.00,
    descrizione VARCHAR(255),
    attiva BOOLEAN NOT NULL DEFAULT 1,
    predefinita BOOLEAN NOT NULL DEFAULT 0,
    data_creazione DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_aggiornamento DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_vat_rates_nome ON vat_rates (nome);
CREATE INDEX ix_vat_rates_attiva ON vat_rates (attiva);
CREATE INDEX ix_vat_rates_predefinita ON vat_rates (predefinita);

CREATE TABLE customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome VARCHAR(100) NOT NULL,
    cognome VARCHAR(100),
    ragione_sociale VARCHAR(140),
    email VARCHAR(120),
    telefono VARCHAR(40),
    codice_fiscale VARCHAR(20) UNIQUE,
    partita_iva VARCHAR(20) UNIQUE,
    indirizzo VARCHAR(255),
    note TEXT,
    attivo BOOLEAN NOT NULL DEFAULT 1,
    data_creazione DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_aggiornamento DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_customers_nome ON customers (nome);
CREATE INDEX ix_customers_cognome ON customers (cognome);
CREATE INDEX ix_customers_ragione_sociale ON customers (ragione_sociale);
CREATE INDEX ix_customers_email ON customers (email);
CREATE INDEX ix_customers_telefono ON customers (telefono);
CREATE INDEX ix_customers_codice_fiscale ON customers (codice_fiscale);
CREATE INDEX ix_customers_partita_iva ON customers (partita_iva);
CREATE INDEX ix_customers_attivo ON customers (attivo);

CREATE TABLE shop_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chiave VARCHAR(80) NOT NULL UNIQUE,
    valore VARCHAR(255) NOT NULL DEFAULT '',
    descrizione VARCHAR(255),
    data_creazione DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_aggiornamento DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_shop_preferences_chiave ON shop_preferences (chiave);

CREATE TABLE suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome VARCHAR(120) NOT NULL UNIQUE,
    email VARCHAR(120),
    telefono VARCHAR(40),
    indirizzo VARCHAR(255),
    note TEXT,
    data_creazione DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_aggiornamento DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_suppliers_nome ON suppliers (nome);

CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome VARCHAR(140) NOT NULL,
    categoria_id INTEGER NOT NULL,
    marca_id INTEGER NOT NULL,
    compatibilita_id INTEGER,
    formato_confezione VARCHAR(120),
    prezzo_acquisto NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    prezzo_vendita NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    quantita_disponibile INTEGER NOT NULL DEFAULT 0,
    quantita_minima_alert INTEGER NOT NULL DEFAULT 0,
    sku_barcode VARCHAR(80) UNIQUE,
    immagine_url VARCHAR(255),
    fornitore_id INTEGER,
    note TEXT,
    attivo BOOLEAN NOT NULL DEFAULT 1,
    data_creazione DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_aggiornamento DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (categoria_id) REFERENCES categories(id),
    FOREIGN KEY (marca_id) REFERENCES brands(id),
    FOREIGN KEY (compatibilita_id) REFERENCES compatibilities(id),
    FOREIGN KEY (fornitore_id) REFERENCES suppliers(id)
);
CREATE INDEX ix_products_nome ON products (nome);
CREATE INDEX ix_products_categoria_id ON products (categoria_id);
CREATE INDEX ix_products_marca_id ON products (marca_id);
CREATE INDEX ix_products_compatibilita_id ON products (compatibilita_id);
CREATE INDEX ix_products_quantita_disponibile ON products (quantita_disponibile);
CREATE INDEX ix_products_sku_barcode ON products (sku_barcode);
CREATE INDEX ix_products_attivo ON products (attivo);
CREATE INDEX ix_products_nome_marca ON products (nome, marca_id);
CREATE INDEX ix_products_categoria_attivo ON products (categoria_id, attivo);

CREATE TABLE sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_ora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    totale_lordo NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    sconto_tipo VARCHAR(20) NOT NULL DEFAULT 'nessuno',
    sconto_valore NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    totale_netto NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    metodo_pagamento VARCHAR(30) NOT NULL DEFAULT 'contanti',
    note_cliente VARCHAR(255),
    customer_id INTEGER,
    vat_rate_id INTEGER,
    aliquota_iva_snapshot NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    totale_iva NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    operatore_id INTEGER NOT NULL,
    stato VARCHAR(20) NOT NULL DEFAULT 'completata',
    margine_stimato NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (vat_rate_id) REFERENCES vat_rates(id),
    FOREIGN KEY (operatore_id) REFERENCES users(id)
);
CREATE INDEX ix_sales_data_ora ON sales (data_ora);
CREATE INDEX ix_sales_operatore_id ON sales (operatore_id);
CREATE INDEX ix_sales_customer_id ON sales (customer_id);
CREATE INDEX ix_sales_vat_rate_id ON sales (vat_rate_id);
CREATE INDEX ix_sales_stato ON sales (stato);
CREATE INDEX ix_sales_data_ora_stato ON sales (data_ora, stato);
CREATE INDEX ix_sales_pagamento ON sales (metodo_pagamento);

CREATE TABLE sale_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendita_id INTEGER NOT NULL,
    prodotto_id INTEGER NOT NULL,
    quantita INTEGER NOT NULL,
    prezzo_unitario NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    subtotale NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    costo_unitario_snapshot NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    margine_riga NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    FOREIGN KEY (vendita_id) REFERENCES sales(id),
    FOREIGN KEY (prodotto_id) REFERENCES products(id)
);
CREATE INDEX ix_sale_items_vendita_id ON sale_items (vendita_id);
CREATE INDEX ix_sale_items_prodotto_id ON sale_items (prodotto_id);
CREATE INDEX ix_sale_items_sale_prodotto ON sale_items (vendita_id, prodotto_id);

CREATE TABLE inventory_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_movimento VARCHAR(40) NOT NULL,
    data_ora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    prodotto_id INTEGER NOT NULL,
    quantita INTEGER NOT NULL,
    motivo VARCHAR(255),
    costo_unitario NUMERIC(10,2) DEFAULT 0.00,
    operatore_id INTEGER NOT NULL,
    riferimento_entita VARCHAR(80),
    note TEXT,
    FOREIGN KEY (prodotto_id) REFERENCES products(id),
    FOREIGN KEY (operatore_id) REFERENCES users(id)
);
CREATE INDEX ix_inventory_movements_tipo_movimento ON inventory_movements (tipo_movimento);
CREATE INDEX ix_inventory_movements_data_ora ON inventory_movements (data_ora);
CREATE INDEX ix_inventory_movements_prodotto_id ON inventory_movements (prodotto_id);
CREATE INDEX ix_inventory_movements_operatore_id ON inventory_movements (operatore_id);
CREATE INDEX ix_inventory_movements_riferimento_entita ON inventory_movements (riferimento_entita);
CREATE INDEX ix_inventory_movements_data_tipo ON inventory_movements (data_ora, tipo_movimento);

CREATE TABLE activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    utente_id INTEGER NOT NULL,
    azione VARCHAR(120) NOT NULL,
    entita_tipo VARCHAR(60) NOT NULL,
    entita_id VARCHAR(60),
    dettagli TEXT,
    data_ora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (utente_id) REFERENCES users(id)
);
CREATE INDEX ix_activity_logs_utente_id ON activity_logs (utente_id);
CREATE INDEX ix_activity_logs_data_ora ON activity_logs (data_ora);
CREATE INDEX ix_activity_logs_data_azione ON activity_logs (data_ora, azione);
