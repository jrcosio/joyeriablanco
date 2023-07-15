/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/javafx/FXMLController.java to edit this template
 */
package com.jrblanco.joyeriablanco.core.componentes.mensajedialog;

import java.net.URL;
import java.util.ResourceBundle;
import javafx.event.ActionEvent;
import javafx.fxml.FXML;
import javafx.fxml.Initializable;
import javafx.scene.control.Button;
import javafx.scene.control.Label;
import javafx.stage.Stage;

/**
 * FXML Controller class
 *
 * @author JRBlanco
 */
public class MensajeDialogController implements Initializable {

    private Stage stage;
    
    @FXML
    private Label lbTexto;
    @FXML
    private Button btnAceptar;

    /**
     * Initializes the controller class.
     */
    @Override
    public void initialize(URL url, ResourceBundle rb) {
        // TODO
    }    

    @FXML
    private void onClickBtnAceptar(ActionEvent event) {
         stage.close();
    }
    
    public void setStage(Stage stage) {
        this.stage = stage;
    }

    public Label getLbTexto() {
        return lbTexto;
    }
    
    
}
