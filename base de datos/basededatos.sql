CREATE DATABASE joyeriablanco;
USE joyeriablanco;

CREATE TABLE Clientes (
    id INT NOT NULL AUTO_INCREMENT,
    nif VARCHAR(9) NOT NULL UNIQUE,
    nombre VARCHAR(80),
    direccion VARCHAR(80),
    localidad VARCHAR(40),
    provincia VARCHAR(40),
    telefono VARCHAR(11),
    PRIMARY KEY (id)
)ENGINE=InnoDB;

CREATE TABLE Facturas (
    idfactura INT NOT NULL AUTO_INCREMENT,
    nif VARCHAR(9) NOT NULL,
    fecha DATE NOT NULL,
    sumaimporte DECIMAL(10,2) NOT NULL,
    iva DECIMAL(10,2) NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (idfactura),
    FOREIGN KEY (nif) REFERENCES Clientes(nif)
)ENGINE=InnoDB;

CREATE TABLE DetalleFactura (
    id INT NOT NULL AUTO_INCREMENT,
    idfactura INT NOT NULL,
    cantidad INT NOT NULL,
    descripcion VARCHAR(255) NOT NULL,
    precio DECIMAL(10,2) NOT NULL,
    importe DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (idfactura) REFERENCES Facturas(idfactura)
)ENGINE=InnoDB;

CREATE TABLE Presupuestos (
    idpresupuesto INT NOT NULL AUTO_INCREMENT,
    nif VARCHAR(9) NOT NULL,
    fecha DATE NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (idpresupuesto),
    FOREIGN KEY (nif) REFERENCES Clientes(nif)
)ENGINE=InnoDB;

CREATE TABLE DetallePresupuesto (
    id INT NOT NULL AUTO_INCREMENT,
    idpresupuesto INT NOT NULL,
    cantidad INT NOT NULL,
    descripcion VARCHAR(255) NOT NULL,
    precio DECIMAL(10,2) NOT NULL,
    importe DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (idpresupuesto) REFERENCES Presupuestos(idpresupuesto)
)ENGINE=InnoDB;

