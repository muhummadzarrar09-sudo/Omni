#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

// OMNI V2 - Tauri Hybrid - Rust Shell + Python Sidecar - Fable 5 + GPT 5.6 Sol
// Spawns Python FastAPI sidecar as binary, manages lifecycle, IPC via HTTP

use std::{
    env,
    io::{BufRead, BufReader},
    process::{Child, Command, Stdio},
    sync::{Arc, Mutex},
    thread,
};

use tauri::{Manager, RunEvent};

fn backend_filename() -> &'static str {
    if cfg!(windows) {
        "omni-backend.exe"
    } else {
        "omni-backend"
    }
}

fn spawn_backend() -> std::io::Result<Child> {
    let exe_path = env::current_exe().expect("failed to get current exe path");
    let exe_dir = exe_path.parent().expect("failed to get parent dir of exe");

    // Try multiple locations for backend binary
    let possible_paths = vec![
        exe_dir.join(backend_filename()),
        exe_dir.join("bin").join("api").join(backend_filename()),
        exe_dir.join("..").join("bin").join("api").join(backend_filename()),
        PathBuf::from("src-tauri/bin/api").join(backend_filename()),
        PathBuf::from("src/backends/dist").join(backend_filename()),
    ];

    let mut backend_path = None;
    for path in possible_paths {
        if path.exists() {
            backend_path = Some(path);
            break;
        }
    }

    let backend_path = backend_path.unwrap_or_else(|| {
        // Fallback: try python -m omni_v2.tools as sidecar via python
        // For dev: run python backend directly
        println!("No compiled backend found, trying python -m src.backends.main");
        PathBuf::from("python")
    });

    println!("▶ Looking for sidecar at {:?}", backend_path);

    let mut child = if backend_path.extension().and_then(|s| s.to_str()) == Some("exe") || backend_path.to_string_lossy().contains("omni-backend") {
        // Compiled binary
        Command::new(&backend_path)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()?
    } else {
        // For dev: spawn python FastAPI sidecar
        // Try .venv/Scripts/python.exe on Windows or python3 on Linux/Mac
        let python_exe = if cfg!(windows) {
            let venv_python = PathBuf::from(".venv/Scripts/python.exe");
            if venv_python.exists() {
                venv_python
            } else {
                PathBuf::from("python")
            }
        } else {
            let venv_python = PathBuf::from(".venv/bin/python");
            if venv_python.exists() {
                venv_python
            } else {
                PathBuf::from("python3")
            }
        };

        println!("▶ Spawning Python sidecar via {:?} -m src.backends.main", python_exe);

        Command::new(python_exe)
            .arg("-m")
            .arg("src.backends.main")
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()?
    };

    if let Some(out) = child.stdout.take() {
        thread::spawn(move || {
            for line in BufReader::new(out).lines().flatten() {
                println!("[backend] {}", line);
            }
        });
    }

    if let Some(err) = child.stderr.take() {
        thread::spawn(move || {
            for line in BufReader::new(err).lines().flatten() {
                eprintln!("[backend-err] {}", line);
            }
        });
    }

    println!("▶ Spawned backend: {:?}", backend_path);
    Ok(child)
}

use std::path::PathBuf;

#[tauri::command]
async fn execute_command(text: String) -> Result<String, String> {
    // Call Python sidecar FastAPI /execute endpoint
    // For Phase 5, mock - Phase 6 will do real HTTP call to localhost:8000
    println!("[Rust] execute_command called: {}", text);

    // Try to call Python sidecar via HTTP
    match reqwest::get(format!("http://localhost:8000/execute?text={}", urlencoding::encode(&text))).await {
        Ok(resp) => {
            let body = resp.text().await.unwrap_or_else(|_| "Failed to read response".to_string());
            Ok(body)
        }
        Err(e) => {
            // Fallback mock for Phase 5 demo
            println!("[Rust] Python sidecar not running ({}), using mock", e);
            Ok(format!("MOCK EXECUTED: {} - Chain 2 steps: Opened + Searched (Rust shell + Python sidecar will do real in Phase 6)", text))
        }
    }
}

#[tauri::command]
async fn get_system_stats() -> Result<String, String> {
    // Get system stats for dashboard - Phase 5 mock, Phase 6 real via psutil via sidecar
    Ok(r#"{"cpu": 15.5, "ram": 45.2, "mic_level": 0.02}"#.to_string())
}

#[tauri::command]
async fn set_mic_muted(muted: bool) -> Result<String, String> {
    println!("[Rust] set_mic_muted: {}", muted);
    Ok(format!("Mic {}", if muted { "muted" } else { "unmuted" }))
}

fn main() {
    let child_handle = Arc::new(Mutex::new(None::<Child>));

    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_global_shortcut::init())
        .setup({
            let child_handle = child_handle.clone();
            move |_app_handle| {
                // Spawn Python backend sidecar
                match spawn_backend() {
                    Ok(child) => {
                        *child_handle.lock().unwrap() = Some(child);
                        println!("✅ Python sidecar spawned successfully");
                    }
                    Err(e) => {
                        eprintln!("⚠️ Failed to spawn Python backend: {} - will use mock mode", e);
                        println!("⚠️ Running in mock mode - frontend will work but Python tools will be mocked");
                    }
                }
                Ok(())
            }
        })
        .invoke_handler(tauri::generate_handler![execute_command, get_system_stats, set_mic_muted])
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    let exit_handle = child_handle.clone();
    app.run(move |_app_handle, event| {
        if let RunEvent::Exit = event {
            if let Some(mut child) = exit_handle.lock().unwrap().take() {
                let _ = child.kill();
                println!("⛔ Backend terminated - OMNI V2 shutting down");
            }
        }
    });
}
