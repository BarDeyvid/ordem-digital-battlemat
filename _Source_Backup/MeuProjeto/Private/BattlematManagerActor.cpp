#include "BattlematManagerActor.h"
#include "Components/BoxComponent.h"
#include "BattlematCoordinateMapper.h"

ABattlematManagerActor::ABattlematManagerActor()
{
	PrimaryActorTick.bCanEverTick = false;

	TableBounds = CreateDefaultSubobject<UBoxComponent>(TEXT("TableBounds"));
	RootComponent = TableBounds;
	// Define tamanho padrão proporcional a um monitor 16:9 de 24" (aprox. 1200 x 675 unidades)
	TableBounds->SetBoxExtent(FVector(675.0f, 1200.0f, 500.0f));
	TableBounds->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	UdpReceiver = CreateDefaultSubobject<UUDPReceiverComponent>(TEXT("UdpReceiver"));

	DefaultTokenClass = ABattlematTokenActor::StaticClass();
}

void ABattlematManagerActor::BeginPlay()
{
	Super::BeginPlay();

	if (UdpReceiver)
	{
		UdpReceiver->OnTokenReceived.AddDynamic(this, &ABattlematManagerActor::HandleTokenTelemetry);
	}
}

void ABattlematManagerActor::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (UdpReceiver)
	{
		UdpReceiver->OnTokenReceived.RemoveDynamic(this, &ABattlematManagerActor::HandleTokenTelemetry);
	}
	Super::EndPlay(EndPlayReason);
}

void ABattlematManagerActor::HandleTokenTelemetry(int32 TokenId, const FString& TokenType, FVector2D NormalizedPos, float Rotation)
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}

	const FVector Origin = TableBounds->GetComponentLocation();
	const FVector BoxExtent = TableBounds->GetScaledBoxExtent();
	const FVector2D Extent2D(BoxExtent.Y, BoxExtent.X);

	FVector TargetWorldLoc;
	FVector SurfaceNormal;

	// Executa projeção de raio vertical até a superfície do mapa 3D
	const bool bHit = UBattlematCoordinateMapper::MapNormalizedToWorldSurface(
		this,
		NormalizedPos,
		Origin,
		Extent2D,
		BoxExtent.Z,
		-BoxExtent.Z * 2.0f,
		ECC_Visibility,
		TargetWorldLoc,
		SurfaceNormal
	);

	// Converte rotação
	const FRotator TargetRot = UBattlematCoordinateMapper::ConvertArucoRotationToUnrealRotator(
		Rotation,
		YawOffset,
		bInvertRotation
	);

	// Localiza ou spawna o ator do token correspondente
	ABattlematTokenActor* TokenActor = nullptr;
	if (ActiveTokens.Contains(TokenId))
	{
		TokenActor = ActiveTokens[TokenId];
	}

	if (!IsValid(TokenActor))
	{
		FActorSpawnParameters SpawnParams;
		SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		SpawnParams.Owner = this;

		TSubclassOf<ABattlematTokenActor> ClassToSpawn = DefaultTokenClass ? DefaultTokenClass : ABattlematTokenActor::StaticClass();
		TokenActor = World->SpawnActor<ABattlematTokenActor>(ClassToSpawn, TargetWorldLoc, TargetRot, SpawnParams);

		if (TokenActor)
		{
			TokenActor->InitializeToken(TokenId, TokenType);
			ActiveTokens.Add(TokenId, TokenActor);
			BP_OnTokenSpawned(TokenActor);
		}
	}

	if (IsValid(TokenActor))
	{
		TokenActor->UpdateTargetPose(TargetWorldLoc, TargetRot);
	}
}

void ABattlematManagerActor::SetMembranaLevel(int32 NewLevel)
{
	MembranaLevel = FMath::Clamp(NewLevel, 0, 3);
	BP_OnMembranaStateChanged(MembranaLevel);
}

ABattlematTokenActor* ABattlematManagerActor::GetTokenById(int32 TokenId) const
{
	if (ActiveTokens.Contains(TokenId))
	{
		return ActiveTokens[TokenId];
	}
	return nullptr;
}

TArray<ABattlematTokenActor*> ABattlematManagerActor::GetAllActiveTokens() const
{
	TArray<ABattlematTokenActor*> Result;
	ActiveTokens.GenerateValueArray(Result);
	return Result;
}
