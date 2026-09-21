#include "BattlematTokenActor.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"

ABattlematTokenActor::ABattlematTokenActor()
{
	PrimaryActorTick.bCanEverTick = true;

	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	RootComponent = SceneRoot;

	BaseAuraMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("BaseAuraMesh"));
	BaseAuraMesh->SetupAttachment(RootComponent);
	BaseAuraMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	BaseAuraMesh->SetCastShadow(false);

	DirectionMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("DirectionMesh"));
	DirectionMesh->SetupAttachment(RootComponent);
	DirectionMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	DirectionMesh->SetCastShadow(false);
}

void ABattlematTokenActor::BeginPlay()
{
	Super::BeginPlay();
	TargetLocation = GetActorLocation();
	TargetRotation = GetActorRotation();
}

void ABattlematTokenActor::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	// Interpolação suave para evitar trepidação da câmera e dar sensação fluida aos efeitos visuais
	const FVector CurrentLoc = GetActorLocation();
	const FRotator CurrentRot = GetActorRotation();

	const FVector NewLoc = FMath::VInterpTo(CurrentLoc, TargetLocation, DeltaTime, LocationInterpSpeed);
	const FRotator NewRot = FMath::RInterpTo(CurrentRot, TargetRotation, DeltaTime, RotationInterpSpeed);

	SetActorLocationAndRotation(NewLoc, NewRot);

	// Checagem de presença física na mesa
	TimeSinceLastPacket += DeltaTime;
	if (bIsPhysicallyPresent && TimeSinceLastPacket > TimeoutToLift)
	{
		bIsPhysicallyPresent = false;
		BP_OnTokenLifted();
	}
}

void ABattlematTokenActor::UpdateTargetPose(const FVector& NewWorldLocation, const FRotator& NewWorldRotation)
{
	TargetLocation = NewWorldLocation;
	TargetRotation = NewWorldRotation;

	if (!bIsPhysicallyPresent)
	{
		bIsPhysicallyPresent = true;
		BP_OnTokenPlaced();
	}

	TimeSinceLastPacket = 0.0f;
	BP_OnTokenMoved(NewWorldLocation, NewWorldRotation);
}

void ABattlematTokenActor::InitializeToken(int32 InTokenId, const FString& InTokenType)
{
	TokenId = InTokenId;
	TokenType = InTokenType;

	Element = UParanormalTypeUtils::ParseElementFromType(InTokenType);
	Category = UParanormalTypeUtils::ParseCategoryFromType(InTokenType);
	ThemeColor = UParanormalTypeUtils::GetElementThemeColor(Element);

	// Ajusta raio de visão padrão por categoria
	if (Category == ETokenCategory::Investigador)
	{
		VisionRadius = 450.0f;
	}
	else if (Category == ETokenCategory::Criatura)
	{
		VisionRadius = 300.0f;
	}

	BP_OnElementVisualsUpdated(Element, ThemeColor);
}

void ABattlematTokenActor::UpdateCharacterStatus(const FString& InName, float InPvPct, float InSanPct, float InPePct, int32 InPvAtual, int32 InPvMax, int32 InSanAtual, int32 InSanMax, int32 InPeAtual, int32 InPeMax)
{
	CharacterName = InName;
	PVPercent = FMath::Clamp(InPvPct, 0.0f, 1.0f);
	SANPercent = FMath::Clamp(InSanPct, 0.0f, 1.0f);
	PEPercent = FMath::Clamp(InPePct, 0.0f, 1.0f);

	BP_OnCharacterStatusUpdated(PVPercent, SANPercent, PEPercent);
}

void ABattlematTokenActor::TriggerRitualCast(const FString& RitualName, const FString& InElement, float RangeMeters, int32 PeCost)
{
	BP_OnRitualCast(RitualName, InElement, RangeMeters);
}
