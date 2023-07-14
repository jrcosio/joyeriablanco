package com.jrblanco.joyeriablanco;

import com.jrblanco.joyeriablanco.core.VentanasNavigation;
import javafx.application.Application;
import javafx.fxml.FXMLLoader;
import javafx.scene.Scene;
import javafx.stage.Stage;

import java.io.IOException;

/**
 * JavaFX App
 */
public class App extends Application {

    @Override
    public void start(Stage stage) throws IOException {
        FXMLLoader fxmlLoader = new FXMLLoader(App.class.getResource(VentanasNavigation.MainFXML));
        Scene scene = new Scene(fxmlLoader.load(), 1000, 600);
        //stage.getIcons().add(new Image(AppPrincipal.class.getResourceAsStream("imagenes/B_Logo.png")));
        stage.setTitle("Gestión Joyería Blanco S.C.");
        stage.setScene(scene);
        stage.show();
    }


    public static void main(String[] args) {
        launch();
    }

}