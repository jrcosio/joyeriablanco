/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/javafx/FXMLController.java to edit this template
 */
package com.jrblanco.joyeriablanco.main;

import java.net.URL;
import java.util.ResourceBundle;
import javafx.event.ActionEvent;
import javafx.fxml.FXML;
import javafx.fxml.Initializable;

import javafx.scene.control.Button;
import javafx.scene.input.MouseEvent;
import javafx.scene.layout.AnchorPane;
import javafx.scene.layout.Pane;
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
        // TODO
    }    
    
    @FXML
    private void onClickSalirApp(ActionEvent event) {
    }

    @FXML
    private void onClickMenuPrincipal(MouseEvent event) {
    }

    @FXML
    private void onClickMenuClientes(MouseEvent event) {
    }

    @FXML
    private void onClickMenuFacturas(MouseEvent event) {
    }

    @FXML
    private void onClickMenuPresupuestos(MouseEvent event) {
    }
}
