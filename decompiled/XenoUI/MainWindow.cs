using System;
using System.CodeDom.Compiler;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Markup;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Imaging;
using System.Windows.Shapes;
using System.Windows.Threading;
using Microsoft.Web.WebView2.Wpf;
using Microsoft.Win32;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace XenoUI;

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
