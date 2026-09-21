using UnrealBuildTool;
using System.Collections.Generic;

public class MeuProjetoEditorTarget : TargetRules
{
	public MeuProjetoEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("MeuProjeto");
	}
}
