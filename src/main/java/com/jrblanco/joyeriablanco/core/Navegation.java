package com.jrblanco.joyeriablanco.core;

import com.jrblanco.joyeriablanco.App;
import java.io.IOException;
import javafx.fxml.FXMLLoader;
import javafx.scene.layout.AnchorPane;

/**
 *
 * @author JRBlanco
 */
public class Navegation {
    /**
     * Método que carga en el AnchorPane principal un formulario
     *
     * @param content donde se quiere incrustar
     * @param ficheroFXML formulario a cargar
     */
    public static void load(AnchorPane content, String ficheroFXML) {
        try {
            AnchorPane pane = FXMLLoader.load(App.class.getResource(ficheroFXML));
            //pane.setPrefSize(contentPrincipal.getWidth(),contentPrincipal.getHeight());
            AnchorPane.setBottomAnchor(pane, 0.0); //Establece al nuevo panel restricciones para que ocupe el espacio
            AnchorPane.setRightAnchor(pane, 0.0);
            AnchorPane.setTopAnchor(pane, 0.0);
            AnchorPane.setLeftAnchor(pane, 0.0);
            content.getChildren().setAll(pane);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }
}
