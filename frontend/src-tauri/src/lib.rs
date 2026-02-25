use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_os::init())
        .plugin(tauri_plugin_notification::init())
        .setup(|app| {
            let window = app.get_webview_window("main").unwrap();
            window.set_title("Regia - Document Intelligence").ok();
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running Regia");
}
