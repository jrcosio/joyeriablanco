/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.jrblanco.joyeriablanco.core.componentes.mensajedialog;

import com.jrblanco.joyeriablanco.App;
import com.jrblanco.joyeriablanco.core.componentes.confirmdialog.ConfirmDialogController;
import javafx.fxml.FXMLLoader;
import javafx.scene.Parent;
import javafx.scene.Scene;
import javafx.stage.Modality;
import javafx.stage.Stage;

/**
 *
 * @author JRBlanco
 */
public class MensajeDialog {
    
    public static void show(String title, String Mensaje) {
        try {
            // Crea una nueva ventana (Stage)
            Stage dialogStage = new Stage();
            dialogStage.setTitle(title);
            dialogStage.setResizable(false);
            dialogStage.setMaximized(false);

            // Carga la vista desde el archivo fxml
            FXMLLoader loader = new FXMLLoader(App.class.getResource("MensajeDialog.fxml"));
            Parent root = loader.load();

            // Puedes obtener el controlador del fxml si lo necesitas
            MensajeDialogController controller = loader.getController();
            controller.setStage(dialogStage);  // asumiendo que tienes este método en tu controlador

            controller.getLbTexto().setText(Mensaje);
            // Configura la ventana como un diálogo modal
            dialogStage.initModality(Modality.APPLICATION_MODAL);

            // Configura la escena y la muestra
            Scene scene = new Scene(root);
            dialogStage.setScene(scene);
            dialogStage.showAndWait();
            
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
    
}
