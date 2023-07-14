module com.jrblanco.joyeriablanco {
    requires javafx.controls;
    requires javafx.fxml;
    requires java.base;

    opens com.jrblanco.joyeriablanco to javafx.fxml;
    exports com.jrblanco.joyeriablanco;
       
    opens com.jrblanco.joyeriablanco.main to javafx.fxml;
    exports com.jrblanco.joyeriablanco.main;
    
}
