/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/javafx/FXMLController.java to edit this template
 */
package com.jrblanco.joyeriablanco.main;

import com.jrblanco.joyeriablanco.App;
import com.jrblanco.joyeriablanco.core.Navegation;
import com.jrblanco.joyeriablanco.core.VentanasNavigation;
import com.jrblanco.joyeriablanco.core.componentes.confirmdialog.ConfirmDialog;
import com.jrblanco.joyeriablanco.core.componentes.mensajedialog.MensajeDialog;
import java.io.IOException;
import java.net.URL;
import java.util.Optional;
import java.util.ResourceBundle;
import javafx.event.ActionEvent;
import javafx.fxml.FXML;
import javafx.fxml.FXMLLoader;
import javafx.fxml.Initializable;
import javafx.scene.control.Alert;

import javafx.scene.control.Button;
import javafx.scene.control.ButtonBar;
import javafx.scene.control.ButtonType;
import javafx.scene.input.MouseEvent;
import javafx.scene.layout.AnchorPane;
import javafx.scene.layout.Pane;
import javafx.stage.Stage;

/**
 * FXML Controller class
 *
 * @author JRBlanco
 */
public class MainViewController implements Initializable {

    @FXML
    private Button btnSalirApp;
    @FXML
    private Pane btnPrincipal;
    @FXML
    private Pane btnClientes;
    @FXML
    private Pane btnFacturas;
    @FXML
    private Pane btnPresupuestos;
    @FXML
    private AnchorPane contentPrincipal;

    /**
     * Initializes the controller class.
     */
    @Override
    public void initialize(URL url, ResourceBundle rb) {
        
    }

    @FXML
    private void onClickSalirApp(ActionEvent event) {

        boolean result = ConfirmDialog.show("¿Salir de la aplicación?", "¿Estás seguro que deseas salir de la aplicación?");
        
        if (result == true) {
            // Obtener la escena del menú y luego el Stage
            Stage stage = (Stage) btnSalirApp.getScene().getWindow(); //.getParentPopup().getOwnerWindow();
            stage.close();
        }        
    }

    @FXML
    private void onClickMenuPrincipal(MouseEvent event) {
        // Navegation.load(contentPrincipal,VentanasNavigation.FacturasFXML);
    }

    @FXML
    private void onClickMenuClientes(MouseEvent event) {
        Navegation.load(contentPrincipal,VentanasNavigation.ClientesFXML);
    }

    @FXML
    private void onClickMenuFacturas(MouseEvent event) {
        Navegation.load(contentPrincipal,VentanasNavigation.FacturasFXML);
    }

    @FXML
    private void onClickMenuPresupuestos(MouseEvent event) {
        // Navegation.load(contentPrincipal,VentanasNavigation.PresupuestosFXML);
        MensajeDialog.show("HOLA", "HOLA MUNDO CRUEL");
    }

    /**
     * Crea una veentana de dialogo con un texto a confirmar
     * @param titulo titulo de la ventana
     * @param texto texto para confirmar
     * @param tipo  icono
     * @return retorna una alert (Ejemplo de uso):
     *       Optional<ButtonType> result = showMensaje("titulo", "texto", Alert.AlertType.CONFIRMATION).showAndWait();
     * 
     *       // Controlar el resultado
     *       if (result.isPresent() && result.get().getButtonData() == ButtonBar.ButtonData.OK_DONE) {
     *          OK
     *       } else {
     *          CANCEL
     *       }
     */
    public  Alert showMensaje(String titulo, String texto, Alert.AlertType tipo) {
        Alert alert = new Alert(tipo);
        // Crear dos botones personalizados
        ButtonType btnConfirmar = new ButtonType("Confirmar", ButtonBar.ButtonData.OK_DONE);
        ButtonType btnCancelar = new ButtonType("Cancelar", ButtonBar.ButtonData.CANCEL_CLOSE);
        // Elimina los botones por defecto
        alert.getButtonTypes().clear();
        // Añadir botones personalizados
        alert.getButtonTypes().addAll(btnConfirmar, btnCancelar);
        alert.setHeaderText(null);
        alert.setTitle(titulo);
        alert.setContentText(texto);
        // Devuelve la alerta para manejarla fuera
        return alert;
    }
    
    

    
    

}
