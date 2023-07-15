/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/javafx/FXMLController.java to edit this template
 */
package com.jrblanco.joyeriablanco.clientes;

import java.net.URL;
import java.util.ResourceBundle;
import javafx.event.ActionEvent;
import javafx.fxml.FXML;
import javafx.fxml.Initializable;
import javafx.scene.control.Button;
import javafx.scene.control.CheckBox;
import javafx.scene.control.TableColumn;
import javafx.scene.control.TableView;
import javafx.scene.control.TextField;

/**
 * FXML Controller class
 *
 * @author JRBlanco
 */
public class ClientesViewController implements Initializable {

    @FXML
    private TextField etxtBuscar;
    @FXML
    private Button btnBuscar;
    @FXML
    private TableView<?> tablaClientes;
    @FXML
    private TableColumn<?, ?> columnaId;
    @FXML
    private TableColumn<?, ?> columnaNif;
    @FXML
    private TableColumn<?, ?> columnaNombre;
    @FXML
    private TableColumn<?, ?> columnaDirecc;
    @FXML
    private TableColumn<?, ?> columnaLocal;
    @FXML
    private TableColumn<?, ?> columnaTlfno;
    @FXML
    private CheckBox mostrarTodos;

    /**
     * Initializes the controller class.
     */
    @Override
    public void initialize(URL url, ResourceBundle rb) {
        // TODO
    }    

    @FXML
    private void onClickBtnBuscar(ActionEvent event) {
    }

    @FXML
    private void btnBorrar(ActionEvent event) {
    }

    @FXML
    private void btnEditar(ActionEvent event) {
    }

    @FXML
    private void btnNuevo(ActionEvent event) {
    }

    @FXML
    private void onClickMostrarTodos(ActionEvent event) {
    }
    
}
