module com.jrblanco.joyeriablanco {
    requires javafx.controls;
    requires javafx.fxml;
    requires java.base;

    opens com.jrblanco.joyeriablanco to javafx.fxml;
    exports com.jrblanco.joyeriablanco;
       
    opens com.jrblanco.joyeriablanco.main to javafx.fxml;
    exports com.jrblanco.joyeriablanco.main;
    
    opens com.jrblanco.joyeriablanco.clientes to javafx.fxml;
    exports com.jrblanco.joyeriablanco.clientes;
    
    opens com.jrblanco.joyeriablanco.facturas to javafx.fxml;
    exports com.jrblanco.joyeriablanco.facturas;
    
    opens com.jrblanco.joyeriablanco.core.componentes.confirmdialog to javafx.fxml;
    exports com.jrblanco.joyeriablanco.core.componentes.confirmdialog;
    
    opens com.jrblanco.joyeriablanco.core.componentes.mensajedialog to javafx.fxml;
    exports com.jrblanco.joyeriablanco.core.componentes.mensajedialog;
}
    
