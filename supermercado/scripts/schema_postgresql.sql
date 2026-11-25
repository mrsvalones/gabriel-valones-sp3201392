BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001

CREATE TABLE categories (
    id SERIAL NOT NULL, 
    name VARCHAR(80) NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (name)
);

CREATE TABLE suppliers (
    id SERIAL NOT NULL, 
    name VARCHAR(120) NOT NULL, 
    contact VARCHAR(180) NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (name)
);

CREATE TABLE users (
    id SERIAL NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    email VARCHAR(180) NOT NULL, 
    password_hash VARCHAR(255) NOT NULL, 
    role VARCHAR(20) NOT NULL, 
    active BOOLEAN NOT NULL, 
    version INTEGER NOT NULL, 
    failures INTEGER NOT NULL, 
    locked_until TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    CHECK (role IN ('admin','operator')), 
    UNIQUE (email)
);

CREATE TABLE audit (
    id SERIAL NOT NULL, 
    user_id INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    action VARCHAR(200) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE TABLE cash_sessions (
    id SERIAL NOT NULL, 
    user_id INTEGER NOT NULL, 
    opened_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    closed_at TIMESTAMP WITH TIME ZONE, 
    opening NUMERIC(12, 2) NOT NULL, 
    expected NUMERIC(12, 2), 
    counted NUMERIC(12, 2), 
    difference NUMERIC(12, 2), 
    PRIMARY KEY (id), 
    CHECK (opening >= 0), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX uq_open_cash_user ON cash_sessions (user_id) WHERE closed_at IS NULL;

CREATE TABLE products (
    id SERIAL NOT NULL, 
    sku VARCHAR(40) NOT NULL, 
    name VARCHAR(120) NOT NULL, 
    category_id INTEGER NOT NULL, 
    unit VARCHAR(4) NOT NULL, 
    price NUMERIC(12, 2) NOT NULL, 
    cost NUMERIC(12, 2) NOT NULL, 
    stock NUMERIC(12, 3) NOT NULL, 
    minimum NUMERIC(12, 3) NOT NULL, 
    active BOOLEAN NOT NULL, 
    PRIMARY KEY (id), 
    CHECK (unit IN ('UN','KG')), 
    CHECK (cost >= 0), 
    CHECK (minimum >= 0), 
    CHECK (price > 0), 
    CHECK (stock >= 0), 
    FOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE RESTRICT, 
    UNIQUE (sku)
);

CREATE TABLE purchases (
    id SERIAL NOT NULL, 
    key VARCHAR(36) NOT NULL, 
    supplier_id INTEGER NOT NULL, 
    user_id INTEGER NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    reference VARCHAR(80) NOT NULL, 
    total NUMERIC(12, 2) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(supplier_id) REFERENCES suppliers (id) ON DELETE RESTRICT, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT, 
    UNIQUE (key)
);

CREATE TABLE reset_tokens (
    id SERIAL NOT NULL, 
    user_id INTEGER NOT NULL, 
    digest VARCHAR(64) NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    used BOOLEAN NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT, 
    UNIQUE (digest)
);

CREATE TABLE cash_movements (
    id SERIAL NOT NULL, 
    cash_id INTEGER NOT NULL, 
    kind VARCHAR(15) NOT NULL, 
    amount NUMERIC(12, 2) NOT NULL, 
    reason VARCHAR(200) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CHECK (kind IN ('supply','withdrawal')), 
    CHECK (amount > 0), 
    FOREIGN KEY(cash_id) REFERENCES cash_sessions (id) ON DELETE RESTRICT
);

CREATE TABLE purchase_items (
    id SERIAL NOT NULL, 
    purchase_id INTEGER NOT NULL, 
    product_id INTEGER NOT NULL, 
    quantity NUMERIC(12, 3) NOT NULL, 
    cost NUMERIC(12, 2) NOT NULL, 
    subtotal NUMERIC(12, 2) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT, 
    FOREIGN KEY(purchase_id) REFERENCES purchases (id) ON DELETE RESTRICT
);

CREATE TABLE sales (
    id SERIAL NOT NULL, 
    key VARCHAR(36) NOT NULL, 
    user_id INTEGER NOT NULL, 
    cash_id INTEGER NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    total NUMERIC(12, 2) NOT NULL, 
    cash_received NUMERIC(12, 2) NOT NULL, 
    change NUMERIC(12, 2) NOT NULL, 
    status VARCHAR(15) NOT NULL, 
    cancel_reason VARCHAR(200), 
    PRIMARY KEY (id), 
    CHECK (status IN ('completed','cancelled')), 
    CHECK (total > 0), 
    FOREIGN KEY(cash_id) REFERENCES cash_sessions (id) ON DELETE RESTRICT, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT, 
    UNIQUE (key)
);

CREATE INDEX ix_sales_created_at ON sales (created_at);

CREATE TABLE stock_movements (
    id SERIAL NOT NULL, 
    product_id INTEGER NOT NULL, 
    user_id INTEGER NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    quantity NUMERIC(12, 3) NOT NULL, 
    balance NUMERIC(12, 3) NOT NULL, 
    reason VARCHAR(200) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE TABLE ledger (
    id SERIAL NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    user_id INTEGER NOT NULL, 
    sale_id INTEGER, 
    purchase_id INTEGER, 
    description VARCHAR(200) NOT NULL, 
    amount NUMERIC(12, 2) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(purchase_id) REFERENCES purchases (id) ON DELETE RESTRICT, 
    FOREIGN KEY(sale_id) REFERENCES sales (id) ON DELETE RESTRICT, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_ledger_created_at ON ledger (created_at);

CREATE TABLE payments (
    id SERIAL NOT NULL, 
    sale_id INTEGER NOT NULL, 
    method VARCHAR(12) NOT NULL, 
    amount NUMERIC(12, 2) NOT NULL, 
    reference VARCHAR(50) NOT NULL, 
    PRIMARY KEY (id), 
    CHECK (method IN ('cash','debit','credit','pix')), 
    CHECK (amount > 0), 
    FOREIGN KEY(sale_id) REFERENCES sales (id) ON DELETE RESTRICT
);

CREATE TABLE sale_items (
    id SERIAL NOT NULL, 
    sale_id INTEGER NOT NULL, 
    product_id INTEGER NOT NULL, 
    name VARCHAR(120) NOT NULL, 
    sku VARCHAR(40) NOT NULL, 
    unit VARCHAR(4) NOT NULL, 
    quantity NUMERIC(12, 3) NOT NULL, 
    price NUMERIC(12, 2) NOT NULL, 
    cost NUMERIC(12, 2) NOT NULL, 
    subtotal NUMERIC(12, 2) NOT NULL, 
    PRIMARY KEY (id), 
    CHECK (quantity > 0), 
    FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT, 
    FOREIGN KEY(sale_id) REFERENCES sales (id) ON DELETE RESTRICT
);

INSERT INTO alembic_version (version_num) VALUES ('0001') RETURNING alembic_version.version_num;

COMMIT;

