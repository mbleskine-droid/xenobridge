using System;
using System.CodeDom.Compiler;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Markup;
using System.Windows.Media.Animation;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace XenoUI;

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
		string path = Path.Combine(_mainWindow.xenoLoc, "FORCED_UI_SETTINGS_PATCH");
		pSettings = Path.Combine(_mainWindow.xenoLoc, "settings.json");
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
			Directory.Delete(Path.Combine(_mainWindow.xenoLoc, "Tabs"), recursive: true);
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
