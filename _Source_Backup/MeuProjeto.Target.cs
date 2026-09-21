using UnrealBuildTool;
using System.Collections.Generic;

public class MeuProjetoTarget : TargetRules
{
	public MeuProjetoTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("MeuProjeto");
	}
}
