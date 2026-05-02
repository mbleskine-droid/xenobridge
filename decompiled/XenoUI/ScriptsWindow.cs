using System;
using System.CodeDom.Compiler;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Markup;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Threading;

namespace XenoUI;

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
		scriptsDirectory = Path.Combine(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Xeno"), "scripts");
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
		string fileName = Path.GetFileName(filePath);
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
