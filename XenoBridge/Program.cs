using System;
using System.IO;
using System.Linq;
using System.Net;
using System.Text;
using System.Text.Json;
using System.Runtime.InteropServices;
using System.Text.Json.Serialization;

namespace XenoBridge;

class Program
{
    static void Main(string[] args)
    {
        var bridge = new XenoBridge();
        var server = new XenoHttpServer(bridge);
        
        Console.WriteLine("🚀 XenoBridge démarré");
        Console.WriteLine("   Port: 3111");
        Console.WriteLine("   Endpoints:");
        Console.WriteLine("   - POST /attach       -> Attacher à Roblox");
        Console.WriteLine("   - POST /execute      -> Exécuter script Lua");
        Console.WriteLine("   - GET  /clients      -> Liste des clients");
        Console.WriteLine("   - POST /setting      -> Modifier paramètre");
        Console.WriteLine("   - GET  /version      -> Version de Xeno");
        Console.WriteLine("   - GET  /health       -> Statut du bridge");
        Console.WriteLine("   - POST /result/{id}  -> Stocker un résultat");
        Console.WriteLine("   - GET  /result/{id}  -> Récupérer un résultat");
        Console.WriteLine();
        
        try
        {
            server.Start();
            Console.WriteLine("✅ Serveur HTTP démarré sur http://localhost:3111");
            Console.WriteLine("   Appuyez sur Ctrl+C pour arrêter");
            Console.WriteLine();
            
            // Boucle infinie pour garder le programme actif
            while (true)
            {
                Thread.Sleep(1000);
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"❌ Erreur: {ex.Message}");
            Console.WriteLine(ex.StackTrace);
        }
    }
}

// Wrapper pour les appels à Xeno.dll
public class XenoBridge
{
    private string _xenoDllPath;
    private bool _initialized = false;
    
    public XenoBridge()
    {
        // Chercher Xeno.dll dans le répertoire courant ou parent
        var currentDir = Directory.GetCurrentDirectory();
        var parentDir = Directory.GetParent(currentDir)?.FullName;
        
        string[] possiblePaths = new string[]
        {
            Path.Combine(currentDir, "Xeno.dll"),
            Path.Combine(currentDir, "Xeno-v1.3.30", "Xeno.dll"),
            Path.Combine(parentDir!, "Xeno-v1.3.30", "Xeno.dll"),
            Path.Combine(parentDir!, "Xeno.dll"),
        };
        
        foreach (var path in possiblePaths)
        {
            if (File.Exists(path))
            {
                _xenoDllPath = path;
                break;
            }
        }
        
        if (string.IsNullOrEmpty(_xenoDllPath))
        {
            throw new FileNotFoundException("Xeno.dll non trouvée. Placez-la dans le même dossier.");
        }
        
        Console.WriteLine($"📦 Xeno.dll trouvée: {_xenoDllPath}");
        
        // Définir le répertoire de travail pour que Xeno.dll trouve ses dépendances
        var xenoDir = Path.GetDirectoryName(_xenoDllPath)!;
        Directory.SetCurrentDirectory(xenoDir);
        
        // Initialiser la DLL
        try
        {
            Initialize(false);
            _initialized = true;
            Console.WriteLine("✅ Xeno.dll initialisée");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"⚠️ Erreur initialisation: {ex.Message}");
            throw;
        }
    }
    
    // P/Invoke pour les exports de Xeno.dll
    [DllImport("Xeno.dll", CallingConvention = CallingConvention.Cdecl)]
    private static extern void Initialize(bool useConsole);
    
    [DllImport("Xeno.dll", CallingConvention = CallingConvention.Cdecl)]
    public static extern void Attach();
    
    [DllImport("Xeno.dll", CallingConvention = CallingConvention.Cdecl)]
    public static extern IntPtr GetClients();
    
    [DllImport("Xeno.dll", CallingConvention = CallingConvention.Cdecl)]
    public static extern void Execute(byte[] script, int[] PIDs, int count);
    
    [DllImport("Xeno.dll", CallingConvention = CallingConvention.Cdecl)]
    public static extern void SetSetting(UISetting settingID, int value);
    
    [DllImport("Xeno.dll", CallingConvention = CallingConvention.Cdecl)]
    public static extern IntPtr Version();
    
    public string GetVersion()
    {
        var ptr = Version();
        if (ptr == IntPtr.Zero) return "unknown";
        return Marshal.PtrToStringAnsi(ptr) ?? "unknown";
    }
    
    public void DoAttach()
    {
        Attach();
    }
    
    public List<ClientInfo> GetClientsList()
    {
        var clients = new List<ClientInfo>();
        var ptr = GetClients();
        
        if (ptr == IntPtr.Zero) return clients;
        
        string json = Marshal.PtrToStringAnsi(ptr) ?? "[]";
        if (string.IsNullOrEmpty(json)) return clients;
        
        try
        {
            // Format: [[pid, username, version, state, id], ...]
            var array = JsonSerializer.Deserialize<List<List<JsonElement>>>(json);
            if (array == null) return clients;
            
            foreach (var item in array)
            {
                if (item.Count >= 4)
                {
                    clients.Add(new ClientInfo
                    {
                        Pid = item[0].GetInt32(),
                        Name = item[1].GetString() ?? "Unknown",
                        Version = item[2].GetString() ?? "Unknown",
                        State = item[3].GetInt32()
                    });
                }
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"⚠️ Erreur parsing clients: {ex.Message}");
        }
        
        return clients;
    }
    
    public void ExecuteScript(string script, int[] pids)
    {
        if (pids == null || pids.Length == 0)
        {
            throw new ArgumentException("Aucun PID spécifié");
        }
        
        // Ajouter null terminator
        var scriptBytes = Encoding.UTF8.GetBytes(script + "\0");
        Execute(scriptBytes, pids, pids.Length);
    }
    
    public void SetUISetting(UISetting setting, bool enabled)
    {
        SetSetting(setting, enabled ? 1 : 0);
    }
    
    public bool IsInitialized => _initialized;
}

public enum UISetting
{
    AutoAttach = 0,
    DiscordRPC = 1
}

// ─── In-Memory Result Store (for HTTP callback) ──────────────────────────
public static class ResultStore
{
    private static readonly System.Collections.Concurrent.ConcurrentDictionary<string, (string content, DateTime expiry)> _store = new();
    private static readonly TimeSpan _ttl = TimeSpan.FromMinutes(2);

    public static void Set(string id, string content)
    {
        _store[id] = (content, DateTime.UtcNow.Add(_ttl));
        Cleanup();
    }

    public static string? Get(string id)
    {
        if (_store.TryGetValue(id, out var entry))
        {
            if (DateTime.UtcNow > entry.expiry)
            {
                _store.TryRemove(id, out _);
                return null;
            }
            return entry.content;
        }
        return null;
    }

    private static void Cleanup()
    {
        var now = DateTime.UtcNow;
        foreach (var kvp in _store)
        {
            if (now > kvp.Value.expiry) _store.TryRemove(kvp.Key, out _);
        }
    }
}

public class ClientInfo
{
    [JsonPropertyName("pid")]
    public int Pid { get; set; }
    
    [JsonPropertyName("name")]
    public string Name { get; set; } = "";
    
    [JsonPropertyName("version")]
    public string Version { get; set; } = "";
    
    [JsonPropertyName("state")]
    public int State { get; set; }
}

public class XenoHttpServer
{
    private readonly HttpListener _listener;
    private readonly XenoBridge _bridge;
    private readonly Thread _listenerThread;
    
    public XenoHttpServer(XenoBridge bridge)
    {
        _bridge = bridge;
        _listener = new HttpListener();
        _listener.Prefixes.Add("http://localhost:3111/");
        _listenerThread = new Thread(HandleRequests);
    }
    
    public void Start()
    {
        _listener.Start();
        _listenerThread.Start();
    }
    
    public void Stop()
    {
        _listener.Stop();
    }
    
    private void HandleRequests()
    {
        while (_listener.IsListening)
        {
            try
            {
                var context = _listener.GetContext();
                _ = Task.Run(() => ProcessRequest(context));
            }
            catch (Exception ex)
            {
                Console.WriteLine($"⚠️ Erreur listener: {ex.Message}");
            }
        }
    }
    
    private async Task ProcessRequest(HttpListenerContext context)
    {
        var request = context.Request;
        var response = context.Response;
        
        // CORS headers
        response.Headers.Add("Access-Control-Allow-Origin", "*");
        response.Headers.Add("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
        response.Headers.Add("Access-Control-Allow-Headers", "Content-Type");
        
        if (request.HttpMethod == "OPTIONS")
        {
            response.StatusCode = 200;
            response.Close();
            return;
        }
        
        string path = request.Url?.AbsolutePath ?? "/";
        string method = request.HttpMethod;
        
        Console.WriteLine($"   {method} {path}");
        
        try
        {
            string responseText = "";
            int statusCode = 200;
            string contentType = "application/json";
            
            switch (path)
            {
                case "/health":
                    responseText = JsonSerializer.Serialize(new { 
                        status = "ok", 
                        initialized = _bridge.IsInitialized,
                        version = _bridge.GetVersion()
                    });
                    break;
                    
                case "/version":
                    responseText = JsonSerializer.Serialize(new { 
                        version = _bridge.GetVersion() 
                    });
                    break;
                    
                case "/clients":
                    if (method == "GET")
                    {
                        var clients = _bridge.GetClientsList();
                        responseText = JsonSerializer.Serialize(new { clients });
                    }
                    else
                    {
                        statusCode = 405;
                        responseText = JsonSerializer.Serialize(new { error = "Method not allowed" });
                    }
                    break;
                    
                case "/attach":
                    if (method == "POST")
                    {
                        _bridge.DoAttach();
                        responseText = JsonSerializer.Serialize(new { 
                            success = true, 
                            message = "Attach déclenché" 
                        });
                    }
                    else
                    {
                        statusCode = 405;
                        responseText = JsonSerializer.Serialize(new { error = "Method not allowed" });
                    }
                    break;
                    
                case "/execute":
                    if (method == "POST")
                    {
                        using var reader = new StreamReader(request.InputStream);
                        string body = await reader.ReadToEndAsync();
                        var data = JsonSerializer.Deserialize<ExecuteRequest>(body);
                        
                        if (data?.Script == null)
                        {
                            statusCode = 400;
                            responseText = JsonSerializer.Serialize(new { error = "Script requis" });
                        }
                        else
                        {
                            // Déterminer les PIDs cibles
                            int[] targetPids = data.PIDs ?? Array.Empty<int>();
                            int autoDetectedPid = 0;
                            
                            // Si aucun PID fourni, chercher automatiquement un client en state 3
                            if (targetPids.Length == 0)
                            {
                                var clients = _bridge.GetClientsList();
                                var readyClient = clients.FirstOrDefault(c => c.State == 3);
                                
                                if (readyClient != null)
                                {
                                    targetPids = new int[] { readyClient.Pid };
                                    autoDetectedPid = readyClient.Pid;
                                    Console.WriteLine($"   🔍 PID auto-détecté: {readyClient.Pid} ({readyClient.Name})");
                                }
                            }
                            
                            if (targetPids.Length == 0)
                            {
                                statusCode = 400;
                                responseText = JsonSerializer.Serialize(new { 
                                    error = "Aucun client prêt (state=3) trouvé. Veuillez fournir un PID manuellement ou attendre que Roblox soit attaché." 
                                });
                            }
                            else
                            {
                                _bridge.ExecuteScript(data.Script, targetPids);
                                responseText = JsonSerializer.Serialize(new { 
                                    success = true, 
                                    executed_on = targetPids,
                                    auto_detected = autoDetectedPid > 0 ? autoDetectedPid : (int?)null
                                });
                            }
                        }
                    }
                    else
                    {
                        statusCode = 405;
                        responseText = JsonSerializer.Serialize(new { error = "Method not allowed" });
                    }
                    break;
                    
                case string p when p.StartsWith("/result/"):
                    if (method == "POST")
                    {
                        string id = p.Substring("/result/".Length);
                        using var reader = new StreamReader(request.InputStream);
                        string body = await reader.ReadToEndAsync();
                        var data = JsonSerializer.Deserialize<ResultRequest>(body);
                        ResultStore.Set(id, data?.Content ?? "");
                        responseText = JsonSerializer.Serialize(new { success = true, id });
                    }
                    else if (method == "GET")
                    {
                        string id = p.Substring("/result/".Length);
                        var content = ResultStore.Get(id);
                        if (content != null)
                        {
                            responseText = JsonSerializer.Serialize(new { found = true, id, content });
                        }
                        else
                        {
                            statusCode = 404;
                            responseText = JsonSerializer.Serialize(new { found = false, id, error = "Result not found or expired" });
                        }
                    }
                    else
                    {
                        statusCode = 405;
                        responseText = JsonSerializer.Serialize(new { error = "Method not allowed" });
                    }
                    break;

                case "/setting":
                    if (method == "POST")
                    {
                        using var reader = new StreamReader(request.InputStream);
                        string body = await reader.ReadToEndAsync();
                        var data = JsonSerializer.Deserialize<SettingRequest>(body);
                        
                        if (data?.Setting == null)
                        {
                            statusCode = 400;
                            responseText = JsonSerializer.Serialize(new { error = "Setting requis" });
                        }
                        else if (!Enum.TryParse<UISetting>(data.Setting, out var setting))
                        {
                            statusCode = 400;
                            responseText = JsonSerializer.Serialize(new { error = "Setting invalide" });
                        }
                        else
                        {
                            _bridge.SetUISetting(setting, data.Value);
                            responseText = JsonSerializer.Serialize(new { 
                                success = true, 
                                setting = data.Setting,
                                value = data.Value
                            });
                        }
                    }
                    else
                    {
                        statusCode = 405;
                        responseText = JsonSerializer.Serialize(new { error = "Method not allowed" });
                    }
                    break;
                    
                default:
                    statusCode = 404;
                    responseText = JsonSerializer.Serialize(new { error = "Not found" });
                    break;
            }
            
            response.StatusCode = statusCode;
            response.ContentType = contentType;
            
            var buffer = Encoding.UTF8.GetBytes(responseText);
            response.ContentLength64 = buffer.Length;
            await response.OutputStream.WriteAsync(buffer, 0, buffer.Length);
        }
        catch (Exception ex)
        {
            Console.WriteLine($"❌ Erreur: {ex.Message}");
            response.StatusCode = 500;
            var error = JsonSerializer.Serialize(new { error = ex.Message });
            var buffer = Encoding.UTF8.GetBytes(error);
            response.ContentLength64 = buffer.Length;
            await response.OutputStream.WriteAsync(buffer, 0, buffer.Length);
        }
        
        response.Close();
    }
}

// Classes pour les requêtes JSON
public class ExecuteRequest
{
    [JsonPropertyName("script")]
    public string Script { get; set; } = "";
    
    [JsonPropertyName("pids")]
    public int[] PIDs { get; set; } = Array.Empty<int>();
}

public class SettingRequest
{
    [JsonPropertyName("setting")]
    public string Setting { get; set; } = "";

    [JsonPropertyName("value")]
    public bool Value { get; set; }
}

public class ResultRequest
{
    [JsonPropertyName("content")]
    public string Content { get; set; } = "";
}
