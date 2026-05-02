using System;
using System.CodeDom.Compiler;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Collections.Specialized;
using System.ComponentModel;
using System.Diagnostics;
using System.Linq;
using System.Net.Http;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Data;
using System.Windows.Markup;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Threading;
using Newtonsoft.Json;

namespace XenoUI;

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
