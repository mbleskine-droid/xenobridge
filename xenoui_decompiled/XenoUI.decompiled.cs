using System;
using System.CodeDom.Compiler;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Collections.Specialized;
using System.ComponentModel;
using System.Configuration;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Security;
using System.Security.Permissions;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Data;
using System.Windows.Input;
using System.Windows.Markup;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Imaging;
using System.Windows.Resources;
using System.Windows.Shapes;
using System.Windows.Threading;
using Microsoft.Web.WebView2.Wpf;
using Microsoft.Win32;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

[assembly: CompilationRelaxations(8)]
[assembly: RuntimeCompatibility(WrapNonExceptionThrows = true)]
[assembly: Debuggable(DebuggableAttribute.DebuggingModes.IgnoreSymbolStoreSequencePoints)]
[assembly: ThemeInfo(ResourceDictionaryLocation.None, ResourceDictionaryLocation.SourceAssembly)]
[assembly: AssemblyAssociatedContentFile("webview2loader.dll")]
[assembly: TargetFramework(".NETCoreApp,Version=v8.0", FrameworkDisplayName = ".NET 8.0")]
[assembly: AssemblyCompany("XenoUI")]
[assembly: AssemblyConfiguration("Release")]
[assembly: AssemblyCopyright("Rizve")]
[assembly: AssemblyDescription("Xeno - Executor UI")]
[assembly: AssemblyFileVersion("1.3.30")]
[assembly: AssemblyInformationalVersion("1.3.30+87ae4f96f8a0927052c1120167982fb069afd1b4")]
[assembly: AssemblyProduct("Project Xeno by Rizve")]
[assembly: AssemblyTitle("XenoUI")]
[assembly: AssemblyMetadata("RepositoryUrl", "https://github.com/Riz-ve/Xeno/tree/main/XenoUI")]
[assembly: TargetPlatform("Windows8.0")]
[assembly: SupportedOSPlatform("Windows8.0")]
[assembly: SecurityPermission(SecurityAction.RequestMinimum, SkipVerification = true)]
[assembly: AssemblyVersion("1.3.30.0")]
[module: UnverifiableCode]
[module: RefSafetyRules(11)]
namespace XenoUI
{
	public class App : Application
	{
		[DebuggerNonUserCode]
		[GeneratedCode("PresentationBuildTasks", "10.0.5.0")]
		public void InitializeComponent()
		{
			base.StartupUri = new Uri("MainWindow.xaml", UriKind.Relative);
		}

		[STAThread]
		[DebuggerNonUserCode]
		[GeneratedCode("PresentationBuildTasks", "10.0.5.0")]
		public static void Main()
		{
			//IL_0005: Unknown result type (might be due to invalid IL or missing references)
			new SplashScreen("resources/images/splash.png").Show(true);
			App app = new App();
			app.InitializeComponent();
			app.Run();
		}
	}
	public class ClientsWindow : Window, IDisposable, IComponentConnector
	{
		public struct ClientInfo
		{
			public string version;

			public string name;

			public int id;

			public int state;
		}

		public enum UISetting
		{
			AutoAttach,
			DiscordRPC
		}

		private class ClientViewModel : INotifyPropertyChanged
		{
			private string _name;

			private string _version;

			private int _state;

			private bool _isChecked;

			public int Id { get; }

			public string Name
			{
				get
				{
					return _name;
				}
				set
				{
					if (_name != value)
					{
						_name = value;
						Raise("Name");
						Raise("DisplayText");
					}
				}
			}

			public string Version
			{
				get
				{
					return _version;
				}
				set
				{
					if (_version != value)
					{
						_version = value;
						Raise("Version");
					}
				}
			}

			public int State
			{
				get
				{
					return _state;
				}
				set
				{
					if (_state != value)
					{
						_state = value;
						Raise("State");
						Raise("StateBrush");
					}
				}
			}

			public string DisplayText => $"{Name} | PID: {Id}";

			public Brush StateBrush => State switch
			{
				0 => Brushes.Red, 
				1 => Brushes.Yellow, 
				2 => Brushes.Cyan, 
				3 => Brushes.LightGreen, 
				_ => Brushes.White, 
			};

			public bool IsChecked
			{
				get
				{
					return _isChecked;
				}
				set
				{
					if (_isChecked != value)
					{
						_isChecked = value;
						Raise("IsChecked");
					}
				}
			}

			public event PropertyChangedEventHandler? PropertyChanged;

			public ClientViewModel(int id, string name, string version, int state)
			{
				Id = id;
				_name = name;
				_version = version;
				_state = state;
				_isChecked = true;
			}

			private void Raise(string prop)
			{
				this.PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(prop));
			}
		}

		private sealed class ClientService : IDisposable
		{
			private static readonly Lazy<ClientService> _instance = new Lazy<ClientService>(() => new ClientService());

			private readonly ObservableCollection<ClientViewModel> _clients = new ObservableCollection<ClientViewModel>();

			private readonly ConcurrentDictionary<int, ClientViewModel> _clientsById = new ConcurrentDictionary<int, ClientViewModel>();

			private readonly CancellationTokenSource _cts = new CancellationTokenSource();

			private readonly Task _pollTask;

			public static ClientService Instance => _instance.Value;

			public ReadOnlyObservableCollection<ClientViewModel> Clients { get; }

			private ClientService()
			{
				Clients = new ReadOnlyObservableCollection<ClientViewModel>(_clients);
				_pollTask = Task.Run(() => PollLoopAsync(_cts.Token));
			}

			private async Task PollLoopAsync(CancellationToken token)
			{
				while (!token.IsCancellationRequested)
				{
					try
					{
						List<ClientInfo> clientsFromDll_NoMessageBox = GetClientsFromDll_NoMessageBox();
						HashSet<int> second = new HashSet<int>(clientsFromDll_NoMessageBox.Select((ClientInfo c) => c.id));
						foreach (ClientInfo item in clientsFromDll_NoMessageBox)
						{
							if (_clientsById.TryGetValue(item.id, out ClientViewModel value))
							{
								if (value.Name != item.name)
								{
									value.Name = item.name;
								}
								if (value.Version != item.version)
								{
									value.Version = item.version;
								}
								if (value.State != item.state)
								{
									value.State = item.state;
								}
								continue;
							}
							ClientViewModel newVm = new ClientViewModel(item.id, item.name, item.version, item.state);
							if (_clientsById.TryAdd(item.id, newVm))
							{
								((DispatcherObject)Application.Current).Dispatcher.Invoke((Action)delegate
								{
									_clients.Add(newVm);
								});
							}
						}
						foreach (int item2 in _clientsById.Keys.Except(second).ToList())
						{
							if (_clientsById.TryRemove(item2, out ClientViewModel vm))
							{
								((DispatcherObject)Application.Current).Dispatcher.Invoke<bool>((Func<bool>)(() => _clients.Remove(vm)));
							}
						}
					}
					catch
					{
					}
					try
					{
						await Task.Delay(200, token);
					}
					catch
					{
						break;
					}
				}
			}

			public int[] GetSelectedClientPids()
			{
				return (from c in _clients
					where c.IsChecked
					select c.Id).ToArray();
			}

			public void Dispose()
			{
				_cts.Cancel();
				try
				{
					_pollTask.Wait(500);
				}
				catch
				{
				}
				_cts.Dispose();
			}
		}

		public string XenoVersion = "1.3.30";

		private List<string> supportedVersions;

		private readonly Dictionary<int, CheckBox> _checkboxByPid = new Dictionary<int, CheckBox>();

		private bool _subscribedToService;

		internal Button buttonClose;

		internal TextBlock TitleActiveClients;

		internal StackPanel checkBoxContainer;

		private bool _contentLoaded;

		public List<ClientInfo> ActiveClients { get; private set; } = new List<ClientInfo>();

		[DllImport("Xeno.dll", CallingConvention = CallingConvention.Cdecl, CharSet = CharSet.Ansi)]
		private static extern nint GetClients();

		[DllImport("Xeno.dll", CallingConvention = CallingConvention.Cdecl, CharSet = CharSet.Ansi)]
		private static extern nint Version();

		[DllImport("Xeno.dll", CallingConvention = CallingConvention.Cdecl, CharSet = CharSet.Ansi)]
		private static extern void Execute(byte[] script, int[] PIDs, int count);

		[DllImport("Xeno.dll", CallingConvention = CallingConvention.Cdecl)]
		public static extern void SetSetting(UISetting settingID, int value);

		[DllImport("Xeno.dll", CallingConvention = CallingConvention.Cdecl)]
		public static extern void Attach();

		[DllImport("Xeno.dll", CallingConvention = CallingConvention.Cdecl)]
		public static extern void Initialize(bool useConsole);

		public ClientsWindow()
		{
			InitializeComponent();
			base.Opacity = 0.0;
			base.Loaded += delegate
			{
				DoubleAnimation animation = new DoubleAnimation(0.0, 1.0, TimeSpan.FromMilliseconds(150.0));
				BeginAnimation(UIElement.OpacityProperty, animation);
			};
			LoadSupportedVersionAsync();
			base.MouseLeftButtonDown += delegate
			{
				DragMove();
			};
			nint num = Version();
			if (num == IntPtr.Zero)
			{
				return;
			}
			string text = Marshal.PtrToStringAnsi(num);
			if (text != null)
			{
				if (text != "v" + XenoVersion)
				{
					MessageBox.Show($"Mismatch Xeno dll Version (expected: v{XenoVersion}, got: {text}). Download the stable version of Xeno from https://xeno.now", "Xeno Corrupted", MessageBoxButton.OK, MessageBoxImage.Hand);
					MessageBox.Show($"Mismatch Xeno dll Version (expected: v{XenoVersion}, got: {text}). Download the stable version of Xeno from https://xeno.now", "Xeno Corrupted", MessageBoxButton.OK, MessageBoxImage.Hand);
					Environment.Exit(0);
				}
				SubscribeToClientService();
			}
		}

		private async Task LoadSupportedVersionAsync()
		{
			_ = 1;
			try
			{
				using HttpClient client = new HttpClient();
				Version version = new Version((await client.GetStringAsync("https://x3no.pages.dev/version.txt")).Trim());
				if (new Version(XenoVersion) < version)
				{
					MessageBox.Show($"The current version {XenoVersion} is outdated.\n\nPlease download the latest version of Xeno ({version}) from https://xeno.now/download\n\nor get it from our Discord: discord.gg/xe-no", "Outdated Xeno version", MessageBoxButton.OK, MessageBoxImage.Exclamation);
					MessageBox.Show($"The current version {XenoVersion} is outdated.\n\nPlease download the latest version of Xeno ({version}) from https://xeno.now/download\n\nor get it from our Discord: discord.gg/xe-no", "Outdated Xeno version", MessageBoxButton.OK, MessageBoxImage.Exclamation);
					Environment.Exit(0);
				}
				supportedVersions = JsonConvert.DeserializeObject<List<string>>(await client.GetStringAsync("https://x3no.pages.dev/supportedVersions.json"));
			}
			catch (HttpRequestException ex)
			{
				MessageBox.Show("Error fetching versions: " + ex.Message);
			}
			catch (JsonException ex2)
			{
				MessageBox.Show("Error parsing versions: " + ex2.Message);
			}
			catch
			{
			}
		}

		private void SubscribeToClientService()
		{
			if (_subscribedToService)
			{
				return;
			}
			_subscribedToService = true;
			foreach (ClientViewModel client in ClientService.Instance.Clients)
			{
				AddClientCheckBoxFromViewModel(client);
				client.PropertyChanged += ClientVm_PropertyChanged;
			}
			((INotifyCollectionChanged)ClientService.Instance.Clients).CollectionChanged += Clients_CollectionChanged;
			UpdateActiveClientsAndTitle();
		}

		private void Clients_CollectionChanged(object? sender, NotifyCollectionChangedEventArgs e)
		{
			((DispatcherObject)Application.Current).Dispatcher.Invoke((Action)delegate
			{
				if (e.NewItems != null)
				{
					foreach (ClientViewModel newItem in e.NewItems)
					{
						AddClientCheckBoxFromViewModel(newItem);
						newItem.PropertyChanged += ClientVm_PropertyChanged;
					}
				}
				if (e.OldItems != null)
				{
					foreach (ClientViewModel oldItem in e.OldItems)
					{
						RemoveClientCheckBox(oldItem.Id);
						oldItem.PropertyChanged -= ClientVm_PropertyChanged;
					}
				}
				UpdateActiveClientsAndTitle();
			});
		}

		private void ClientVm_PropertyChanged(object? sender, PropertyChangedEventArgs e)
		{
			if (e.PropertyName == "State")
			{
				UpdateActiveClientsAndTitle();
			}
		}

		private void AddClientCheckBoxFromViewModel(ClientViewModel vm)
		{
			if (vm.Name == "N/A" || _checkboxByPid.ContainsKey(vm.Id))
			{
				return;
			}
			CheckBox checkBox = new CheckBox
			{
				DataContext = vm,
				FontFamily = new FontFamily("Franklin Gothic Medium"),
				Background = Brushes.Black
			};
			Binding binding = new Binding("DisplayText")
			{
				Mode = BindingMode.OneWay
			};
			checkBox.SetBinding(ContentControl.ContentProperty, binding);
			Binding binding2 = new Binding("IsChecked")
			{
				Mode = BindingMode.TwoWay
			};
			checkBox.SetBinding(ToggleButton.IsCheckedProperty, binding2);
			Binding binding3 = new Binding("Version")
			{
				Mode = BindingMode.OneWay,
				StringFormat = "Version: {0}"
			};
			checkBox.SetBinding(FrameworkElement.ToolTipProperty, binding3);
			Binding binding4 = new Binding("StateBrush")
			{
				Mode = BindingMode.OneWay
			};
			checkBox.SetBinding(FrameworkElement.TagProperty, binding4);
			checkBox.Checked += CheckBox_CheckedUnchecked;
			checkBox.Unchecked += CheckBox_CheckedUnchecked;
			checkBoxContainer.Children.Add(checkBox);
			_checkboxByPid[vm.Id] = checkBox;
			if (vm.Version != "Player")
			{
				List<string> list = supportedVersions;
				if (list != null && !list.Contains(vm.Version))
				{
					MessageBox.Show($"Xeno might not work on the client {vm.Name} with Version '{vm.Version}'\n\nClick OK to continue using Xeno.", "Version Mismatch", MessageBoxButton.OK, MessageBoxImage.Exclamation);
				}
			}
			UpdateActiveClientsAndTitle();
		}

		private void RemoveClientCheckBox(int pid)
		{
			if (_checkboxByPid.TryGetValue(pid, out CheckBox value))
			{
				value.Checked -= CheckBox_CheckedUnchecked;
				value.Unchecked -= CheckBox_CheckedUnchecked;
				checkBoxContainer.Children.Remove(value);
				_checkboxByPid.Remove(pid);
			}
			UpdateActiveClientsAndTitle();
		}

		private void CheckBox_CheckedUnchecked(object sender, RoutedEventArgs e)
		{
			UpdateSelectedEnableState();
			UpdateActiveClientsAndTitle();
		}

		private void UpdateSelectedEnableState()
		{
			List<CheckBox> list = _checkboxByPid.Values.Where((CheckBox cb) => cb.IsChecked == true).ToList();
			if (list.Count == 1)
			{
				list[0].IsEnabled = false;
				return;
			}
			foreach (CheckBox value in _checkboxByPid.Values)
			{
				value.IsEnabled = true;
			}
		}

		private void UpdateActiveClientsAndTitle()
		{
			if (Application.Current != null)
			{
				if (((DispatcherObject)Application.Current).Dispatcher.CheckAccess())
				{
					action();
				}
				else
				{
					((DispatcherObject)Application.Current).Dispatcher.BeginInvoke((Delegate)new Action(action), Array.Empty<object>());
				}
			}
			void action()
			{
				try
				{
					List<ClientViewModel> list = ClientService.Instance.Clients.Where((ClientViewModel vm) => vm.State == 3).ToList();
					ActiveClients = list.Select((ClientViewModel vm) => new ClientInfo
					{
						name = vm.Name,
						id = vm.Id,
						version = vm.Version,
						state = vm.State
					}).ToList();
					int count = list.Count;
					if (TitleActiveClients != null)
					{
						TitleActiveClients.Text = $"Active Clients ({count})";
					}
				}
				catch
				{
				}
			}
		}

		public int[] GetSelectedClientPidsEXT()
		{
			return ClientService.Instance.GetSelectedClientPids();
		}

		public void ExecuteScript(string script, int[] clientPIDs)
		{
			Execute(Encoding.UTF8.GetBytes(script + "\0"), clientPIDs, clientPIDs.Length);
		}

		private static List<ClientInfo> GetClientsFromDll_NoMessageBox()
		{
			List<ClientInfo> list = new List<ClientInfo>();
			nint clients = GetClients();
			if (clients == IntPtr.Zero)
			{
				return list;
			}
			string value = Marshal.PtrToStringAnsi(clients);
			if (string.IsNullOrEmpty(value))
			{
				return list;
			}
			try
			{
				List<List<object>> list2 = JsonConvert.DeserializeObject<List<List<object>>>(value);
				if (list2 == null)
				{
					return list;
				}
				foreach (List<object> item in list2)
				{
					if (item.Count >= 4 && item[0] is long num && item[1] is string name && item[2] is string version)
					{
						int state = 0;
						if (item[3] is long num2)
						{
							state = (int)num2;
						}
						else if (item[3] is int num3)
						{
							state = num3;
						}
						list.Add(new ClientInfo
						{
							id = (int)num,
							name = name,
							version = version,
							state = state
						});
					}
				}
			}
			catch
			{
			}
			return list;
		}

		private static int GetClientId(string content)
		{
			if (string.IsNullOrEmpty(content))
			{
				return -1;
			}
			string[] array = content.Split(" | PID: ");
			if (array.Length < 2)
			{
				return -1;
			}
			if (int.TryParse(array[1], out var result))
			{
				return result;
			}
			return -1;
		}

		private static string GetClientName(string content)
		{
			if (string.IsNullOrEmpty(content))
			{
				return "";
			}
			return content.Split(" | PID: ")[0].Trim();
		}

		private void buttonClose_Click(object sender, RoutedEventArgs e)
		{
			Hide();
		}

		private Brush GetStateColor(int state)
		{
			return state switch
			{
				0 => Brushes.Red, 
				1 => Brushes.Yellow, 
				2 => Brushes.Cyan, 
				3 => Brushes.LightGreen, 
				_ => Brushes.White, 
			};
		}

		public Brush GetOverallClientStatusColor()
		{
			ReadOnlyObservableCollection<ClientViewModel> clients = ClientService.Instance.Clients;
			if (!clients.Any())
			{
				return Brushes.Transparent;
			}
			List<int> list = clients.Select((ClientViewModel vm) => vm.State).Distinct().ToList();
			if (list.Contains(0))
			{
				return Brushes.Red;
			}
			if (list.Contains(1))
			{
				return Brushes.Yellow;
			}
			if (list.Contains(2))
			{
				return Brushes.Cyan;
			}
			if (list.All((int s) => s == 3))
			{
				return Brushes.LightGreen;
			}
			return Brushes.White;
		}

		protected override void OnClosed(EventArgs e)
		{
			base.OnClosed(e);
			UnsubscribeFromClientService();
		}

		private void UnsubscribeFromClientService()
		{
			if (!_subscribedToService)
			{
				return;
			}
			_subscribedToService = false;
			try
			{
				((INotifyCollectionChanged)ClientService.Instance.Clients).CollectionChanged -= Clients_CollectionChanged;
			}
			catch
			{
			}
			try
			{
				foreach (ClientViewModel client in ClientService.Instance.Clients)
				{
					client.PropertyChanged -= ClientVm_PropertyChanged;
				}
			}
			catch
			{
			}
			foreach (KeyValuePair<int, CheckBox> item in _checkboxByPid.ToList())
			{
				item.Value.Checked -= CheckBox_CheckedUnchecked;
				item.Value.Unchecked -= CheckBox_CheckedUnchecked;
			}
			_checkboxByPid.Clear();
			checkBoxContainer.Children.Clear();
		}

		public void Dispose()
		{
			UnsubscribeFromClientService();
		}

		[DebuggerNonUserCode]
		[GeneratedCode("PresentationBuildTasks", "10.0.5.0")]
		public void InitializeComponent()
		{
			if (!_contentLoaded)
			{
				_contentLoaded = true;
				Uri resourceLocator = new Uri("/XenoUI;V1.3.30;component/clientswindow.xaml", UriKind.Relative);
				Application.LoadComponent(this, resourceLocator);
			}
		}

		[DebuggerNonUserCode]
		[GeneratedCode("PresentationBuildTasks", "10.0.5.0")]
		[EditorBrowsable(EditorBrowsableState.Never)]
		void IComponentConnector.Connect(int connectionId, object target)
		{
			switch (connectionId)
			{
			case 1:
				buttonClose = (Button)target;
				buttonClose.Click += buttonClose_Click;
				break;
			case 2:
				TitleActiveClients = (TextBlock)target;
				break;
			case 3:
				checkBoxContainer = (StackPanel)target;
				break;
			default:
				_contentLoaded = true;
				break;
			}
		}
	}
	public class MainWindow : Window, IComponentConnector
	{
		[ComImport]
		[Guid("00021401-0000-0000-C000-000000000046")]
		private class ShellLink
		{
		}

		[ComImport]
		[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
		[Guid("000214F9-0000-0000-C000-000000000046")]
		private interface IShellLinkW
		{
			void GetPath([Out][MarshalAs(UnmanagedType.LPWStr)] StringBuilder pszFile, int cchMaxPath, nint pfd, int fFlags);

			void GetIDList(out nint ppidl);

			void SetIDList(nint pidl);

			void GetDescription([Out][MarshalAs(UnmanagedType.LPWStr)] StringBuilder pszName, int cchMaxName);

			void SetDescription([MarshalAs(UnmanagedType.LPWStr)] string pszName);

			void GetWorkingDirectory([Out][MarshalAs(UnmanagedType.LPWStr)] StringBuilder pszDir, int cchMaxPath);

			void SetWorkingDirectory([MarshalAs(UnmanagedType.LPWStr)] string pszDir);

			void GetArguments([Out][MarshalAs(UnmanagedType.LPWStr)] StringBuilder pszArgs, int cchMaxPath);

			void SetArguments([MarshalAs(UnmanagedType.LPWStr)] string pszArgs);

			void GetHotkey(out short pwHotkey);

			void SetHotkey(short wHotkey);

			void GetShowCmd(out int piShowCmd);

			void SetShowCmd(int iShowCmd);

			void GetIconLocation([Out][MarshalAs(UnmanagedType.LPWStr)] StringBuilder pszIconPath, int cchIconPath, out int piIcon);

			void SetIconLocation([MarshalAs(UnmanagedType.LPWStr)] string pszIconPath, int iIcon);

			void SetRelativePath([MarshalAs(UnmanagedType.LPWStr)] string pszPathRel, int dwReserved);

			void Resolve(nint hwnd, int fFlags);

			void SetPath([MarshalAs(UnmanagedType.LPWStr)] string pszFile);
		}

		[ComImport]
		[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
		[Guid("0000010b-0000-0000-C000-000000000046")]
		private interface IPersistFile
		{
			void GetClassID(out Guid pClassID);

			void IsDirty();

			void Load([MarshalAs(UnmanagedType.LPWStr)] string pszFileName, uint dwMode);

			void Save([MarshalAs(UnmanagedType.LPWStr)] string pszFileName, bool fRemember);

			void SaveCompleted([MarshalAs(UnmanagedType.LPWStr)] string pszFileName);

			void GetCurFile([MarshalAs(UnmanagedType.LPWStr)] out string ppszFileName);
		}

		public readonly ClientsWindow _clientsWindow = new ClientsWindow();

		private readonly SettingsWindow _settingsWindow;

		private readonly ScriptsWindow _scriptsWindow;

		public readonly string xenoLoc = System.IO.Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Xeno");

		private string sTabsConfig = "";

		internal Button buttonMinimize;

		internal Button buttonMaximize;

		internal Image maximizeImage;

		internal Button buttonClose;

		internal TabControl tabControlScripts;

		internal TabItem buttonAddTab;

		internal WebView2 WebView2Client;

		internal Button buttonExecute;

		internal Button buttonShowMultinstance;

		internal Ellipse ClientStatusIndicator;

		internal Button buttonShowScripts;

		internal Button buttonAttach;

		internal Button buttonClear;

		internal Button buttonSaveFile;

		internal Button buttonOpenFile;

		internal Button buttonOpenSettings;

		private bool _contentLoaded;

		public MainWindow()
		{
			//IL_0084: Unknown result type (might be due to invalid IL or missing references)
			//IL_0089: Unknown result type (might be due to invalid IL or missing references)
			//IL_009d: Unknown result type (might be due to invalid IL or missing references)
			InitializeComponent();
			base.Opacity = 0.0;
			base.Loaded += delegate
			{
				DoubleAnimation animation = new DoubleAnimation(0.0, 1.0, TimeSpan.FromMilliseconds(300.0));
				BeginAnimation(UIElement.OpacityProperty, animation);
			};
			_scriptsWindow = new ScriptsWindow(this);
			_settingsWindow = new SettingsWindow(this);
			base.Closing += async delegate(object? sender, CancelEventArgs e)
			{
				if (MessageBox.Show("Are you sure you want to close Xeno?", "Close Xeno", MessageBoxButton.YesNo, MessageBoxImage.Question) == MessageBoxResult.No)
				{
					e.Cancel = true;
				}
				else
				{
					await SaveChangesAsync();
					Process.GetCurrentProcess().Kill();
				}
			};
			DispatcherTimer val = new DispatcherTimer
			{
				Interval = TimeSpan.FromMilliseconds(100.0)
			};
			val.Tick += delegate
			{
				Brush overallClientStatusColor = _clientsWindow.GetOverallClientStatusColor();
				ClientStatusIndicator.Fill = overallClientStatusColor;
				if (overallClientStatusColor == Brushes.Transparent)
				{
					ClientStatusIndicator.StrokeThickness = 0.0;
				}
				else
				{
					ClientStatusIndicator.StrokeThickness = 1.0;
				}
			};
			val.Start();
			bool flag = false;
			if (Enumerable.Contains(Environment.GetCommandLineArgs(), "-useConsole"))
			{
				flag = true;
			}
			else
			{
				string contents = JsonConvert.SerializeObject(new SettingsWindow.DUISettings(), Formatting.Indented);
				string path = System.IO.Path.Combine(xenoLoc, "settings.json");
				if (!File.Exists(path))
				{
					File.WriteAllText(path, contents);
				}
				try
				{
					JToken.Parse(File.ReadAllText(path));
				}
				catch
				{
					MessageBox.Show("Invalid JSON in settings file. Resetting to default.", "Information", MessageBoxButton.OK, MessageBoxImage.Asterisk);
					File.WriteAllText(path, contents);
				}
				flag = JsonConvert.DeserializeObject<SettingsWindow.UISettings>(File.ReadAllText(path)).ShowConsole;
			}
			Initialize();
			ClientsWindow.Initialize(flag);
		}

		private bool ShortcutExists(string shortcutName)
		{
			return File.Exists(System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory, shortcutName));
		}

		private async void Initialize()
		{
			if (!Directory.Exists(xenoLoc))
			{
				Directory.CreateDirectory(xenoLoc);
			}
			if (!ShortcutExists("workspace"))
			{
				IShellLinkW obj = (IShellLinkW)new ShellLink();
				obj.SetDescription("Workspace Folder");
				obj.SetPath(System.IO.Path.Combine(xenoLoc, "workspace"));
				((IPersistFile)obj).Save(System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "workspace.lnk"), fRemember: false);
			}
			if (!ShortcutExists("scripts"))
			{
				IShellLinkW obj2 = (IShellLinkW)new ShellLink();
				obj2.SetDescription("Scripts Folder");
				obj2.SetPath(System.IO.Path.Combine(xenoLoc, "scripts"));
				((IPersistFile)obj2).Save(System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "scripts.lnk"), fRemember: false);
			}
			if (!ShortcutExists("autoexec"))
			{
				IShellLinkW obj3 = (IShellLinkW)new ShellLink();
				obj3.SetDescription("Auto Execute Folder");
				obj3.SetPath(System.IO.Path.Combine(xenoLoc, "autoexec"));
				((IPersistFile)obj3).Save(System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "autoexec.lnk"), fRemember: false);
			}
			string text = System.IO.Path.Combine(System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "editor"), "index.html");
			if (!File.Exists(text))
			{
				Hide();
				MessageBox.Show("File \"" + text + "\" does not exist", "File Not Found", MessageBoxButton.OK, MessageBoxImage.Hand);
				Process.GetCurrentProcess().Kill();
			}
			WebView2Client.Source = new Uri(text);
			string pTabs = System.IO.Path.Combine(xenoLoc, "Tabs");
			if (!Directory.Exists(pTabs))
			{
				Directory.CreateDirectory(pTabs);
			}
			string pConfig = System.IO.Path.Combine(pTabs, "config.json");
			if (!File.Exists(pConfig))
			{
				await File.WriteAllTextAsync(pConfig, "{}");
			}
			try
			{
				JToken.Parse(await File.ReadAllTextAsync(pConfig));
			}
			catch
			{
				MessageBox.Show("Invalid JSON in tabs config file. Resetting to default.", "Information", MessageBoxButton.OK, MessageBoxImage.Asterisk);
				await File.WriteAllTextAsync(pConfig, "{}");
			}
			Dictionary<string, List<object>> dictionary = JsonConvert.DeserializeObject<Dictionary<string, List<object>>>(await File.ReadAllTextAsync(pConfig));
			if (dictionary == null)
			{
				Hide();
				MessageBox.Show("JsonConvert.DeserializeObject returned null", "Newtonsoft.Json Error", MessageBoxButton.OK, MessageBoxImage.Hand);
				Process.GetCurrentProcess().Kill();
			}
			if (dictionary.Count < 1)
			{
				dictionary[Guid.NewGuid().ToString()] = new List<object> { "Tab 1", true };
			}
			bool flag = false;
			foreach (KeyValuePair<string, List<object>> item in dictionary)
			{
				if ((bool)item.Value[1])
				{
					flag = true;
					break;
				}
			}
			if (!flag)
			{
				dictionary.First().Value[1] = true;
			}
			sTabsConfig = JsonConvert.SerializeObject(dictionary, Formatting.Indented);
			foreach (KeyValuePair<string, List<object>> item2 in dictionary)
			{
				string uid = item2.Key.ToString();
				string header = item2.Value[0].ToString();
				bool num = (bool)item2.Value[1];
				TabItem newTab = new TabItem
				{
					Header = header,
					Uid = uid
				};
				newTab.MouseDoubleClick += TabDoubleClick;
				newTab.PreviewMouseLeftButtonDown += TabSelected;
				ContextMenu contextMenu = new ContextMenu();
				MenuItem menuItem = new MenuItem
				{
					Header = "Delete"
				};
				menuItem.Click += delegate
				{
					DeleteTab(newTab);
				};
				MenuItem menuItem2 = new MenuItem
				{
					Header = "Rename"
				};
				menuItem2.Click += delegate
				{
					TabDoubleClick(newTab, null);
				};
				contextMenu.Items.Add(menuItem);
				contextMenu.Items.Add(menuItem2);
				newTab.ContextMenu = contextMenu;
				tabControlScripts.Items.Insert(tabControlScripts.Items.Count - 1, newTab);
				if (num)
				{
					TabSelected(newTab, null);
				}
			}
			foreach (string item3 in Directory.EnumerateFiles(pTabs, "*.*", SearchOption.AllDirectories))
			{
				string fileName = System.IO.Path.GetFileName(item3);
				bool flag2 = false;
				foreach (KeyValuePair<string, List<object>> item4 in dictionary)
				{
					if (item4.Key.ToString() == fileName)
					{
						flag2 = true;
						break;
					}
				}
				if (!flag2 && fileName != "config.json")
				{
					File.Delete(item3);
				}
			}
			await WebView2Client.EnsureCoreWebView2Async();
			WebView2Client.CoreWebView2.Settings.IsPasswordAutosaveEnabled = false;
			WebView2Client.CoreWebView2.Settings.IsGeneralAutofillEnabled = false;
			WebView2Client.CoreWebView2.Settings.AreDevToolsEnabled = false;
			WebView2Client.CoreWebView2.Settings.AreBrowserAcceleratorKeysEnabled = false;
			WebView2Client.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;
		}

		private async void DeleteTab(TabItem tabItem)
		{
			if (tabControlScripts.Items.Count <= 2)
			{
				MessageBox.Show("Can't delete the last available tab", "Error", MessageBoxButton.OK, MessageBoxImage.Hand);
				return;
			}
			string guid = tabItem.Uid.ToString();
			tabControlScripts.Items.Remove(tabItem);
			Dictionary<string, List<object>> dictionary = JsonConvert.DeserializeObject<Dictionary<string, List<object>>>(sTabsConfig);
			if (dictionary == null)
			{
				MessageBox.Show("JsonConvert.DeserializeObject returned null", "Error", MessageBoxButton.OK, MessageBoxImage.Hand);
				return;
			}
			if (dictionary.ContainsKey(tabItem.Uid))
			{
				dictionary.Remove(tabItem.Uid);
			}
			sTabsConfig = JsonConvert.SerializeObject(dictionary, Formatting.Indented);
			await SaveChangesAsync();
			if ((guid == WebView2Client.Uid || tabControlScripts.SelectedItem == null) && tabControlScripts.Items[tabControlScripts.Items.Count - 2] is TabItem sender)
			{
				TabSelected(sender, null);
			}
		}

		private void buttonAddTab_Click(object sender, MouseButtonEventArgs e)
		{
			if (tabControlScripts.Items.Count - 1 > 10)
			{
				MessageBox.Show("Maximum tabs exceeded", "Warning", MessageBoxButton.OK, MessageBoxImage.Exclamation);
				return;
			}
			Dictionary<string, List<object>> dictionary = JsonConvert.DeserializeObject<Dictionary<string, List<object>>>(sTabsConfig);
			if (dictionary == null)
			{
				MessageBox.Show("JsonConvert.DeserializeObject returned null", "Newtonsoft.Json Error", MessageBoxButton.OK, MessageBoxImage.Hand);
				return;
			}
			string text = Guid.NewGuid().ToString();
			string text2 = $"Tab {tabControlScripts.Items.Count}";
			TabItem newTab = new TabItem
			{
				Header = text2,
				Uid = text
			};
			newTab.MouseDoubleClick += TabDoubleClick;
			newTab.PreviewMouseLeftButtonDown += TabSelected;
			ContextMenu contextMenu = new ContextMenu();
			MenuItem menuItem = new MenuItem
			{
				Header = "Delete"
			};
			menuItem.Click += delegate
			{
				DeleteTab(newTab);
			};
			MenuItem menuItem2 = new MenuItem
			{
				Header = "Rename"
			};
			menuItem2.Click += delegate
			{
				TabDoubleClick(newTab, null);
			};
			contextMenu.Items.Add(menuItem);
			contextMenu.Items.Add(menuItem2);
			newTab.ContextMenu = contextMenu;
			TabSelected(newTab, e);
			tabControlScripts.Items.Insert(tabControlScripts.Items.Count - 1, newTab);
			dictionary[text] = new List<object> { text2, true };
			sTabsConfig = JsonConvert.SerializeObject(dictionary, Formatting.Indented);
			e.Handled = true;
		}

		private async void TabSelected(object sender, MouseButtonEventArgs? e)
		{
			if (!(sender is TabItem tabItem) || !(WebView2Client.Uid != tabItem.Uid))
			{
				return;
			}
			tabControlScripts.SelectedItem = tabItem;
			await SaveChangesAsync();
			WebView2Client.Uid = tabItem.Uid;
			Dictionary<string, List<object>> tabsData = JsonConvert.DeserializeObject<Dictionary<string, List<object>>>(sTabsConfig);
			if (tabsData == null)
			{
				MessageBox.Show("JsonConvert.DeserializeObject returned null", "Newtonsoft.Json Error", MessageBoxButton.OK, MessageBoxImage.Hand);
				return;
			}
			string pTabs = System.IO.Path.Combine(xenoLoc, "Tabs");
			foreach (KeyValuePair<string, List<object>> item in tabsData)
			{
				string guid = item.Key.ToString();
				if (guid == tabItem.Uid.ToString())
				{
					item.Value[1] = true;
					string content = "print(\"Hello, World!\")";
					try
					{
						content = await File.ReadAllTextAsync(System.IO.Path.Combine(pTabs, guid));
					}
					catch
					{
						await File.WriteAllTextAsync(System.IO.Path.Combine(pTabs, guid), content);
					}
					await SetScriptContent(content);
					break;
				}
			}
			foreach (KeyValuePair<string, List<object>> item2 in tabsData)
			{
				if (item2.Key.ToString() != tabItem.Uid.ToString())
				{
					item2.Value[1] = false;
				}
			}
			sTabsConfig = JsonConvert.SerializeObject(tabsData, Formatting.Indented);
			await SaveChangesAsync();
		}

		private void TabDoubleClick(object sender, MouseButtonEventArgs? e)
		{
			TabItem tabItem = sender as TabItem;
			if (tabItem == null || tabItem.IsManipulationEnabled)
			{
				return;
			}
			tabItem.IsManipulationEnabled = true;
			TextBox textBox = new TextBox
			{
				Text = tabItem.Header.ToString(),
				Margin = new Thickness(0.0),
				MaxLength = 15
			};
			textBox.LostFocus += delegate
			{
				EditFinish(tabItem, textBox);
			};
			textBox.KeyDown += delegate(object s, KeyEventArgs args)
			{
				//IL_0001: Unknown result type (might be due to invalid IL or missing references)
				//IL_0007: Invalid comparison between Unknown and I4
				if ((int)args.Key == 6)
				{
					EditFinish(tabItem, textBox);
				}
			};
			tabItem.Header = textBox;
			textBox.Focus();
		}

		private async void EditFinish(TabItem tabItem, TextBox textBox)
		{
			tabItem.IsManipulationEnabled = false;
			Dictionary<string, List<object>> dictionary = JsonConvert.DeserializeObject<Dictionary<string, List<object>>>(sTabsConfig);
			if (dictionary == null)
			{
				MessageBox.Show("JsonConvert.DeserializeObject returned null", "Newtonsoft.Json Error", MessageBoxButton.OK, MessageBoxImage.Hand);
				return;
			}
			tabItem.Header = (string.IsNullOrEmpty(textBox.Text.Trim()) ? "Untitled" : textBox.Text.Trim());
			foreach (KeyValuePair<string, List<object>> item in dictionary)
			{
				if (item.Key.ToString() == tabItem.Uid.ToString())
				{
					item.Value[0] = tabItem.Header.ToString();
					break;
				}
			}
			sTabsConfig = JsonConvert.SerializeObject(dictionary, Formatting.Indented);
			await SaveChangesAsync();
		}

		private async Task SaveChangesAsync()
		{
			await File.WriteAllTextAsync(System.IO.Path.Combine(xenoLoc, "Tabs", "config.json"), sTabsConfig);
			Dictionary<string, List<object>> dictionary = JsonConvert.DeserializeObject<Dictionary<string, List<object>>>(sTabsConfig);
			if (dictionary == null)
			{
				MessageBox.Show("JsonConvert.DeserializeObject returned null", "Newtonsoft.Json Error", MessageBoxButton.OK, MessageBoxImage.Hand);
				return;
			}
			string text = System.IO.Path.Combine(xenoLoc, "Tabs", WebView2Client.Uid.ToString());
			foreach (KeyValuePair<string, List<object>> item in dictionary)
			{
				if (item.Key.ToString() == WebView2Client.Uid.ToString())
				{
					string path = text;
					await File.WriteAllTextAsync(path, await GetScriptContent());
					break;
				}
			}
		}

		public void ExecuteScript(string scriptContent)
		{
			int[] selectedClientPidsEXT = _clientsWindow.GetSelectedClientPidsEXT();
			if (selectedClientPidsEXT == null || selectedClientPidsEXT.Length == 0)
			{
				if (buttonAttach.Visibility == Visibility.Visible)
				{
					MessageBox.Show("No active clients are currently selected.\n\nPress the Attach button to attach to a Client. Restart Xeno if Roblox is already open", "No Client Selected", MessageBoxButton.OK, MessageBoxImage.Exclamation);
				}
				else
				{
					MessageBox.Show("No active clients are currently selected.\n\nMake sure Roblox is open. Restart Xeno if Roblox is already open", "No Client Selected", MessageBoxButton.OK, MessageBoxImage.Exclamation);
				}
			}
			else
			{
				_clientsWindow.ExecuteScript(scriptContent, selectedClientPidsEXT);
			}
		}

		private async void buttonExecute_Click(object sender, RoutedEventArgs e)
		{
			try
			{
				ExecuteScript(await GetScriptContent());
			}
			catch (Exception ex)
			{
				MessageBox.Show("Error executing script: " + ex.ToString(), "Error", MessageBoxButton.OK, MessageBoxImage.Hand);
			}
		}

		private void buttonAttach_Click(object sender, RoutedEventArgs e)
		{
			ClientsWindow.Attach();
		}

		private async Task<string> GetScriptContent()
		{
			await WebView2Client.EnsureCoreWebView2Async();
			string text = await WebView2Client.CoreWebView2.ExecuteScriptAsync("getText()");
			if (text.StartsWith("\"") && text.EndsWith("\""))
			{
				string text2 = text;
				text = text2.Substring(1, text2.Length - 1 - 1);
			}
			return Regex.Unescape(text);
		}

		private static string EscapeForScript(string content)
		{
			return content.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n")
				.Replace("\r", "\\r");
		}

		public async Task SetScriptContent(string content)
		{
			await WebView2Client.EnsureCoreWebView2Async();
			while (await GetScriptContent() == "null")
			{
				await Task.Delay(10);
			}
			string text = EscapeForScript(content);
			await WebView2Client.CoreWebView2.ExecuteScriptAsync("setText(\"" + text + "\")");
		}

		private async void buttonOpenFile_Click(object sender, RoutedEventArgs e)
		{
			OpenFileDialog openFileDialog = new OpenFileDialog
			{
				Filter = "Script files (*.lua;*.luau;*.txt)|*.lua;*.luau;*.txt|All files (*.*)|*.*"
			};
			if (openFileDialog.ShowDialog() == true)
			{
				try
				{
					await SetScriptContent(await File.ReadAllTextAsync(openFileDialog.FileName));
				}
				catch (Exception ex)
				{
					MessageBox.Show("Error loading script: " + ex.ToString(), "Error", MessageBoxButton.OK, MessageBoxImage.Hand);
				}
			}
		}

		private async void buttonSaveFile_Click(object sender, RoutedEventArgs e)
		{
			SaveFileDialog saveFileDialog = new SaveFileDialog
			{
				Filter = "Script files (*.lua;*.luau;*.txt)|*.lua;*.luau;*.txt|All files (*.*)|*.*"
			};
			if (saveFileDialog.ShowDialog() == true)
			{
				try
				{
					string fileName = saveFileDialog.FileName;
					await File.WriteAllTextAsync(fileName, await GetScriptContent(), Encoding.UTF8);
					MessageBox.Show("File saved successfully!", "Success", MessageBoxButton.OK, MessageBoxImage.Asterisk);
				}
				catch (Exception ex)
				{
					MessageBox.Show("Error saving file: " + ex.ToString(), "Error", MessageBoxButton.OK, MessageBoxImage.Hand);
				}
			}
		}

		private async void buttonClear_Click(object sender, RoutedEventArgs e)
		{
			try
			{
				await WebView2Client.CoreWebView2.ExecuteScriptAsync("setText(\"\")");
			}
			catch (Exception ex)
			{
				MessageBox.Show("Error clearing script editor: " + ex.ToString(), "Error", MessageBoxButton.OK, MessageBoxImage.Hand);
			}
		}

		private void buttonMinimize_Click(object sender, RoutedEventArgs e)
		{
			base.WindowState = WindowState.Minimized;
		}

		private void buttonMaximize_Click(object sender, RoutedEventArgs e)
		{
			base.WindowState = ((base.WindowState != WindowState.Maximized) ? WindowState.Maximized : WindowState.Normal);
			maximizeImage.Source = new BitmapImage(new Uri((base.WindowState == WindowState.Maximized) ? "pack://application:,,,/Resources/Images/normalize.png" : "pack://application:,,,/Resources/Images/maximize.png"));
		}

		private async void buttonClose_Click(object sender, RoutedEventArgs e)
		{
			if (MessageBox.Show("Are you sure you want to close Xeno?", "Close", MessageBoxButton.YesNo, MessageBoxImage.Question) != MessageBoxResult.No)
			{
				await SaveChangesAsync();
				WebView2Client?.Dispose();
				Hide();
				Process.GetCurrentProcess().Kill();
			}
		}

		private void Window_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
		{
			DragMove();
		}

		private void buttonShowMultinstance_Click(object sender, RoutedEventArgs e)
		{
			ToggleWindow(_clientsWindow);
		}

		private void buttonShowScripts_Click(object sender, RoutedEventArgs e)
		{
			ToggleWindow(_scriptsWindow);
		}

		private void buttonShowSettings_Click(object sender, RoutedEventArgs e)
		{
			ToggleWindow(_settingsWindow);
		}

		private static void ToggleWindow(Window window)
		{
			if (window.IsVisible)
			{
				window.Hide();
			}
			else
			{
				window.Show();
			}
		}

		protected override void OnClosed(EventArgs e)
		{
			base.OnClosed(e);
			WebView2Client?.Dispose();
		}

		[DebuggerNonUserCode]
		[GeneratedCode("PresentationBuildTasks", "10.0.5.0")]
		public void InitializeComponent()
		{
			if (!_contentLoaded)
			{
				_contentLoaded = true;
				Uri resourceLocator = new Uri("/XenoUI;V1.3.30;component/mainwindow.xaml", UriKind.Relative);
				Application.LoadComponent(this, resourceLocator);
			}
		}

		[DebuggerNonUserCode]
		[GeneratedCode("PresentationBuildTasks", "10.0.5.0")]
		[EditorBrowsable(EditorBrowsableState.Never)]
		void IComponentConnector.Connect(int connectionId, object target)
		{
			switch (connectionId)
			{
			case 1:
				((MainWindow)target).MouseLeftButtonDown += Window_MouseLeftButtonDown;
				break;
			case 2:
				buttonMinimize = (Button)target;
				buttonMinimize.Click += buttonMinimize_Click;
				break;
			case 3:
				buttonMaximize = (Button)target;
				buttonMaximize.Click += buttonMaximize_Click;
				break;
			case 4:
				maximizeImage = (Image)target;
				break;
			case 5:
				buttonClose = (Button)target;
				buttonClose.Click += buttonClose_Click;
				break;
			case 6:
				tabControlScripts = (TabControl)target;
				break;
			case 7:
				buttonAddTab = (TabItem)target;
				buttonAddTab.PreviewMouseDown += buttonAddTab_Click;
				break;
			case 8:
				WebView2Client = (WebView2)target;
				break;
			case 9:
				buttonExecute = (Button)target;
				buttonExecute.Click += buttonExecute_Click;
				break;
			case 10:
				buttonShowMultinstance = (Button)target;
				buttonShowMultinstance.Click += buttonShowMultinstance_Click;
				break;
			case 11:
				ClientStatusIndicator = (Ellipse)target;
				break;
			case 12:
				buttonShowScripts = (Button)target;
				buttonShowScripts.Click += buttonShowScripts_Click;
				break;
			case 13:
				buttonAttach = (Button)target;
				buttonAttach.Click += buttonAttach_Click;
				break;
			case 14:
				buttonClear = (Button)target;
				buttonClear.Click += buttonClear_Click;
				break;
			case 15:
				buttonSaveFile = (Button)target;
				buttonSaveFile.Click += buttonSaveFile_Click;
				break;
			case 16:
				buttonOpenFile = (Button)target;
				buttonOpenFile.Click += buttonOpenFile_Click;
				break;
			case 17:
				buttonOpenSettings = (Button)target;
				buttonOpenSettings.Click += buttonShowSettings_Click;
				break;
			default:
				_contentLoaded = true;
				break;
			}
		}
	}
	public class ScriptsWindow : Window, IComponentConnector
	{
		private readonly string scriptsDirectory;

		private readonly DispatcherTimer updateTimer;

		private readonly Dictionary<string, UIElement> scriptPanels;

		private readonly MainWindow _mainWindow;

		internal Button buttonClose;

		internal Button buttonOpenFolder;

		internal StackPanel scripts_container;

		private bool _contentLoaded;

		public ScriptsWindow(MainWindow mainWindow)
		{
			//IL_007f: Unknown result type (might be due to invalid IL or missing references)
			//IL_0084: Unknown result type (might be due to invalid IL or missing references)
			//IL_009d: Expected O, but got Unknown
			InitializeComponent();
			base.Opacity = 0.0;
			base.Loaded += delegate
			{
				DoubleAnimation animation = new DoubleAnimation(0.0, 1.0, TimeSpan.FromMilliseconds(150.0));
				BeginAnimation(UIElement.OpacityProperty, animation);
			};
			_mainWindow = mainWindow;
			scriptsDirectory = System.IO.Path.Combine(System.IO.Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Xeno"), "scripts");
			scriptPanels = new Dictionary<string, UIElement>();
			base.MouseLeftButtonDown += delegate
			{
				DragMove();
			};
			Directory.CreateDirectory(scriptsDirectory);
			updateTimer = new DispatcherTimer
			{
				Interval = TimeSpan.FromSeconds(0.5)
			};
			updateTimer.Tick += delegate
			{
				UpdateScripts();
			};
			updateTimer.Start();
			LoadScripts();
		}

		private void LoadScripts()
		{
			string[] files = Directory.GetFiles(scriptsDirectory);
			foreach (string filePath in files)
			{
				AddScriptPanel(filePath);
			}
		}

		private void UpdateScripts()
		{
			HashSet<string> hashSet = new HashSet<string>(Directory.GetFiles(scriptsDirectory));
			foreach (string item in scriptPanels.Keys.Except(hashSet).ToList())
			{
				RemoveScriptPanel(item);
			}
			foreach (string item2 in hashSet.Except(scriptPanels.Keys))
			{
				AddScriptPanel(item2);
			}
		}

		private void AddScriptPanel(string filePath)
		{
			string fileName = System.IO.Path.GetFileName(filePath);
			Grid grid = new Grid
			{
				Margin = new Thickness(5.0),
				HorizontalAlignment = HorizontalAlignment.Stretch
			};
			grid.ColumnDefinitions.Add(new ColumnDefinition
			{
				Width = new GridLength(1.0, GridUnitType.Star)
			});
			grid.ColumnDefinitions.Add(new ColumnDefinition
			{
				Width = GridLength.Auto
			});
			TextBlock element = new TextBlock
			{
				Text = fileName,
				Foreground = Brushes.White,
				VerticalAlignment = VerticalAlignment.Center,
				FontFamily = new FontFamily("Cascadia Code"),
				FontSize = 14.0
			};
			Grid.SetColumn(element, 0);
			Button button = new Button
			{
				Content = "Open",
				Margin = new Thickness(10.0, 0.0, 0.0, 0.0),
				Tag = filePath,
				Style = (Style)FindResource("DarkRoundedButtonStyle")
			};
			Grid.SetColumn(button, 1);
			button.Click += async delegate
			{
				string scriptContent = await File.ReadAllTextAsync(filePath);
				await _mainWindow.SetScriptContent(scriptContent);
			};
			Border element2 = new Border
			{
				BorderBrush = Brushes.Gray,
				BorderThickness = new Thickness(0.0, 0.0, 0.0, 1.0),
				Margin = new Thickness(0.0, 5.0, 0.0, 0.0)
			};
			Grid.SetColumn(element2, 0);
			Grid.SetColumnSpan(element2, 2);
			grid.Children.Add(element);
			grid.Children.Add(button);
			grid.Children.Add(element2);
			scripts_container.Children.Add(grid);
			scriptPanels[filePath] = grid;
		}

		private void RemoveScriptPanel(string filePath)
		{
			if (scriptPanels.TryGetValue(filePath, out UIElement value))
			{
				scripts_container.Children.Remove(value);
				scriptPanels.Remove(filePath);
			}
		}

		private void buttonClose_Click(object sender, RoutedEventArgs e)
		{
			Hide();
		}

		private void buttonOpenFolder_Click(object sender, RoutedEventArgs e)
		{
			Process.Start("explorer.exe", scriptsDirectory);
		}

		[DebuggerNonUserCode]
		[GeneratedCode("PresentationBuildTasks", "10.0.5.0")]
		public void InitializeComponent()
		{
			if (!_contentLoaded)
			{
				_contentLoaded = true;
				Uri resourceLocator = new Uri("/XenoUI;V1.3.30;component/scriptswindow.xaml", UriKind.Relative);
				Application.LoadComponent(this, resourceLocator);
			}
		}

		[DebuggerNonUserCode]
		[GeneratedCode("PresentationBuildTasks", "10.0.5.0")]
		[EditorBrowsable(EditorBrowsableState.Never)]
		void IComponentConnector.Connect(int connectionId, object target)
		{
			switch (connectionId)
			{
			case 1:
				buttonClose = (Button)target;
				buttonClose.Click += buttonClose_Click;
				break;
			case 2:
				buttonOpenFolder = (Button)target;
				buttonOpenFolder.Click += buttonOpenFolder_Click;
				break;
			case 3:
				scripts_container = (StackPanel)target;
				break;
			default:
				_contentLoaded = true;
				break;
			}
		}
	}
	public class SettingsWindow : Window, IComponentConnector
	{
		public class UISettings
		{
			[JsonProperty("Auto Attach")]
			public bool AutoAttach { get; set; }

			[JsonProperty("Top Most")]
			public bool TopMost { get; set; }

			[JsonProperty("Discord RPC")]
			public bool UseDiscordRPC { get; set; }

			[JsonProperty("Show Console")]
			public bool ShowConsole { get; set; }
		}

		public class DUISettings
		{
			[JsonProperty("Auto Attach")]
			public bool AutoAttach { get; set; }

			[JsonProperty("Top Most")]
			public bool TopMost { get; set; }

			[JsonProperty("Discord RPC")]
			public bool UseDiscordRPC { get; set; }

			[JsonProperty("Show Console")]
			public bool ShowConsole { get; set; }
		}

		private readonly MainWindow _mainWindow;

		private string pSettings;

		public bool oSSv;

		internal Button buttonClose;

		internal CheckBox CheckBoxAutoAttach;

		internal CheckBox CheckBoxUseConsole;

		internal CheckBox CheckBoxDiscordRPC;

		internal CheckBox CheckBoxTopMost;

		internal Button buttonRestart;

		internal Button buttonResetTabs;

		internal Button buttonJoinDiscord;

		private bool _contentLoaded;

		public SettingsWindow(MainWindow mainWindow)
		{
			InitializeComponent();
			_mainWindow = mainWindow;
			base.Opacity = 0.0;
			base.Loaded += delegate
			{
				DoubleAnimation animation = new DoubleAnimation(0.0, 1.0, TimeSpan.FromMilliseconds(150.0));
				BeginAnimation(UIElement.OpacityProperty, animation);
			};
			base.MouseLeftButtonDown += delegate
			{
				DragMove();
			};
			string path = System.IO.Path.Combine(_mainWindow.xenoLoc, "FORCED_UI_SETTINGS_PATCH");
			pSettings = System.IO.Path.Combine(_mainWindow.xenoLoc, "settings.json");
			if (File.Exists(path))
			{
				File.Delete(path);
			}
			InitializeSettings();
		}

		private async void InitializeSettings()
		{
			DUISettings value = new DUISettings();
			string settingsDefault = JsonConvert.SerializeObject(value, Formatting.Indented);
			if (!File.Exists(pSettings))
			{
				await File.WriteAllTextAsync(pSettings, settingsDefault);
			}
			try
			{
				JToken.Parse(await File.ReadAllTextAsync(pSettings));
			}
			catch
			{
				MessageBox.Show("Invalid JSON in settings file. Resetting to default", "Information", MessageBoxButton.OK, MessageBoxImage.Asterisk);
				await File.WriteAllTextAsync(pSettings, settingsDefault);
			}
			UISettings uISettings = JsonConvert.DeserializeObject<UISettings>(await File.ReadAllTextAsync(pSettings));
			oSSv = uISettings.ShowConsole;
			CheckBoxUseConsole.IsChecked = uISettings.ShowConsole;
			CheckBoxAutoAttach.IsChecked = uISettings.AutoAttach;
			if (uISettings.AutoAttach)
			{
				_mainWindow.buttonAttach.Visibility = Visibility.Hidden;
				ClientsWindow.SetSetting(ClientsWindow.UISetting.AutoAttach, 1);
			}
			else
			{
				_mainWindow.buttonAttach.Visibility = Visibility.Visible;
				ClientsWindow.SetSetting(ClientsWindow.UISetting.AutoAttach, 0);
			}
			_mainWindow.Topmost = uISettings.TopMost;
			CheckBoxTopMost.IsChecked = uISettings.TopMost;
			CheckBoxDiscordRPC.IsChecked = uISettings.UseDiscordRPC;
			ClientsWindow.SetSetting(ClientsWindow.UISetting.DiscordRPC, uISettings.UseDiscordRPC ? 1 : 0);
		}

		private async Task SaveSettingsAsync()
		{
			UISettings value = new UISettings
			{
				AutoAttach = (CheckBoxAutoAttach.IsChecked == true),
				TopMost = (CheckBoxTopMost.IsChecked == true),
				UseDiscordRPC = (CheckBoxDiscordRPC.IsChecked == true),
				ShowConsole = (CheckBoxUseConsole.IsChecked == true)
			};
			await File.WriteAllTextAsync(pSettings, JsonConvert.SerializeObject(value, Formatting.Indented));
		}

		private void buttonClose_Click(object sender, RoutedEventArgs e)
		{
			Hide();
		}

		private async void CheckBoxSettings_Checked(object sender, RoutedEventArgs e)
		{
			if ((sender as CheckBox).IsChecked == true)
			{
				_mainWindow.buttonAttach.Visibility = Visibility.Hidden;
				ClientsWindow.SetSetting(ClientsWindow.UISetting.AutoAttach, 1);
			}
			else
			{
				_mainWindow.buttonAttach.Visibility = Visibility.Visible;
				ClientsWindow.SetSetting(ClientsWindow.UISetting.AutoAttach, 0);
			}
			await SaveSettingsAsync();
		}

		private async void CheckBoxTopMost_Checked(object sender, RoutedEventArgs e)
		{
			CheckBox checkBox = sender as CheckBox;
			_mainWindow.Topmost = checkBox.IsChecked.Value;
			await SaveSettingsAsync();
		}

		private async void CheckBoxDiscordRPC_Checked(object sender, RoutedEventArgs e)
		{
			CheckBox checkBox = sender as CheckBox;
			ClientsWindow.SetSetting(ClientsWindow.UISetting.DiscordRPC, checkBox.IsChecked.Value ? 1 : 0);
			await SaveSettingsAsync();
		}

		private async void CheckBoxUseConsole_Checked(object sender, RoutedEventArgs e)
		{
			CheckBox checkbox = sender as CheckBox;
			if (oSSv != checkbox.IsChecked)
			{
				await SaveSettingsAsync();
				if (checkbox.IsChecked.Value)
				{
					Process.Start(new ProcessStartInfo
					{
						FileName = Process.GetCurrentProcess().MainModule.FileName,
						UseShellExecute = true,
						Arguments = "-useconsole"
					});
					Process.GetCurrentProcess().Kill();
				}
				else
				{
					Process.Start(new ProcessStartInfo
					{
						FileName = Process.GetCurrentProcess().MainModule.FileName,
						UseShellExecute = true
					});
					Process.GetCurrentProcess().Kill();
				}
			}
		}

		private void buttonJoinDiscord_Click(object sender, RoutedEventArgs e)
		{
			Process.Start(new ProcessStartInfo
			{
				FileName = "https://discord.gg/xe-no",
				UseShellExecute = true
			});
		}

		private void buttonResetTabs_Click(object sender, RoutedEventArgs e)
		{
			if (MessageBox.Show("Are you sure you want to delete all tabs?", "Confirmation", MessageBoxButton.YesNo, MessageBoxImage.Exclamation) == MessageBoxResult.Yes)
			{
				Directory.Delete(System.IO.Path.Combine(_mainWindow.xenoLoc, "Tabs"), recursive: true);
				Process.Start(Process.GetCurrentProcess().MainModule.FileName);
			}
		}

		private async void buttonReset_Click(object sender, RoutedEventArgs e)
		{
			if (MessageBox.Show("Are you sure you want to reset all settings?", "Confirmation", MessageBoxButton.YesNo, MessageBoxImage.Exclamation) == MessageBoxResult.Yes)
			{
				string contents = JsonConvert.SerializeObject(new UISettings(), Formatting.Indented);
				await File.WriteAllTextAsync(pSettings, contents);
				InitializeSettings();
			}
		}

		private void buttonRestart_Click(object sender, RoutedEventArgs e)
		{
			Process.Start(Process.GetCurrentProcess().MainModule.FileName);
		}

		[DebuggerNonUserCode]
		[GeneratedCode("PresentationBuildTasks", "10.0.5.0")]
		public void InitializeComponent()
		{
			if (!_contentLoaded)
			{
				_contentLoaded = true;
				Uri resourceLocator = new Uri("/XenoUI;V1.3.30;component/settingswindow.xaml", UriKind.Relative);
				Application.LoadComponent(this, resourceLocator);
			}
		}

		[DebuggerNonUserCode]
		[GeneratedCode("PresentationBuildTasks", "10.0.5.0")]
		[EditorBrowsable(EditorBrowsableState.Never)]
		void IComponentConnector.Connect(int connectionId, object target)
		{
			switch (connectionId)
			{
			case 1:
				buttonClose = (Button)target;
				buttonClose.Click += buttonClose_Click;
				break;
			case 2:
				CheckBoxAutoAttach = (CheckBox)target;
				CheckBoxAutoAttach.Checked += CheckBoxSettings_Checked;
				CheckBoxAutoAttach.Unchecked += CheckBoxSettings_Checked;
				break;
			case 3:
				CheckBoxUseConsole = (CheckBox)target;
				CheckBoxUseConsole.Checked += CheckBoxUseConsole_Checked;
				CheckBoxUseConsole.Unchecked += CheckBoxUseConsole_Checked;
				break;
			case 4:
				CheckBoxDiscordRPC = (CheckBox)target;
				CheckBoxDiscordRPC.Checked += CheckBoxDiscordRPC_Checked;
				CheckBoxDiscordRPC.Unchecked += CheckBoxDiscordRPC_Checked;
				break;
			case 5:
				CheckBoxTopMost = (CheckBox)target;
				CheckBoxTopMost.Checked += CheckBoxTopMost_Checked;
				CheckBoxTopMost.Unchecked += CheckBoxTopMost_Checked;
				break;
			case 6:
				buttonRestart = (Button)target;
				buttonRestart.Click += buttonRestart_Click;
				break;
			case 7:
				buttonResetTabs = (Button)target;
				buttonResetTabs.Click += buttonResetTabs_Click;
				break;
			case 8:
				buttonJoinDiscord = (Button)target;
				buttonJoinDiscord.Click += buttonJoinDiscord_Click;
				break;
			default:
				_contentLoaded = true;
				break;
			}
		}
	}
}
namespace XenoUI.Properties
{
	[CompilerGenerated]
	[GeneratedCode("Microsoft.VisualStudio.Editors.SettingsDesigner.SettingsSingleFileGenerator", "17.10.0.0")]
	internal sealed class Settings : ApplicationSettingsBase
	{
		private static Settings defaultInstance = (Settings)SettingsBase.Synchronized(new Settings());

		public static Settings Default => defaultInstance;
	}
}
