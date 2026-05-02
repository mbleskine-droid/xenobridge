using System;
using System.CodeDom.Compiler;
using System.Diagnostics;
using System.Windows;

namespace XenoUI;

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
