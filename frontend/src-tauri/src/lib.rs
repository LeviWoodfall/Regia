use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use tauri::{Manager, WindowEvent};

#[derive(Clone, Default)]
struct BackendProcess(Arc<Mutex<Option<Child>>>);

impl BackendProcess {
    fn set(&self, child: Child) {
        if let Ok(mut guard) = self.0.lock() {
            *guard = Some(child);
        }
    }

    fn stop(&self) {
        if let Ok(mut guard) = self.0.lock() {
            if let Some(child) = guard.as_mut() {
                let _ = child.kill();
            }
            guard.take();
        }
    }
}

fn start_backend(app: &tauri::AppHandle) -> tauri::Result<Child> {
    let resource_dir = app.path_resolver().resource_dir().expect("Resource dir not found");
    let exe = resource_dir.join("regia-backend");
    let exe_path = if cfg!(windows) {
        exe.with_extension("exe")
    } else {
        exe
    };
    Command::new(exe_path)
        .current_dir(resource_dir)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| tauri::Error::FailedToExecuteApi(format!("Failed to start backend: {}", e)))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let backend_state = BackendProcess::default();
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_os::init())
        .plugin(tauri_plugin_notification::init())
        .setup(move |app| {
            app.manage(backend_state.clone());
            let child = start_backend(app)?;
            backend_state.set(child);

            if let Some(window) = app.get_webview_window("main") {
                window.set_title("Regia - Document Intelligence").ok();
                let backend = backend_state.clone();
                window.on_window_event(move |event| {
                    if let WindowEvent::CloseRequested { .. } = event {
                        backend.stop();
                    }
                });
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running Regia");
}
