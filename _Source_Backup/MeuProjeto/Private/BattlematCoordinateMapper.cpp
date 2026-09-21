#include "BattlematCoordinateMapper.h"

bool UBattlematCoordinateMapper::MapNormalizedToWorldSurface(
	const UObject* WorldContextObject,
	FVector2D NormalizedPos,
	FVector PlayAreaOrigin,
	FVector2D PlayAreaExtent,
	float TraceHeightStart,
	float TraceHeightEnd,
	ECollisionChannel TraceChannel,
	FVector& OutWorldLocation,
	FVector& OutSurfaceNormal
)
{
	OutSurfaceNormal = FVector::UpVector;

	// Clamp de segurança nas coordenadas normalizadas
	const float ClampedX = FMath::Clamp(NormalizedPos.X, 0.0f, 1.0f);
	const float ClampedY = FMath::Clamp(NormalizedPos.Y, 0.0f, 1.0f);

	// Mapeia [0, 1] para [-Extent, +Extent] em torno de PlayAreaOrigin
	// No sistema padrão top-down:
	// X = frente/trás (0 no topo, 1 no fundo) -> Origin.X + (0.5 - ClampedY) * (Extent.Y * 2.0f)
	// Y = esquerda/direita (0 na esquerda, 1 na direita) -> Origin.Y + (ClampedX - 0.5) * (Extent.X * 2.0f)
	const float WorldX = PlayAreaOrigin.X + ((1.0f - ClampedY) - 0.5f) * (PlayAreaExtent.Y * 2.0f);
	const float WorldY = PlayAreaOrigin.Y + (ClampedX - 0.5f) * (PlayAreaExtent.X * 2.0f);

	OutWorldLocation = FVector(WorldX, WorldY, PlayAreaOrigin.Z);

	if (!WorldContextObject)
	{
		return false;
	}

	UWorld* World = WorldContextObject->GetWorld();
	if (!World)
	{
		return false;
	}

	// Executa raycast vertical para encontrar o chão 3D
	const FVector Start(WorldX, WorldY, PlayAreaOrigin.Z + TraceHeightStart);
	const FVector End(WorldX, WorldY, PlayAreaOrigin.Z + TraceHeightEnd);

	FHitResult HitResult;
	FCollisionQueryParams QueryParams(TEXT("BattlematSurfaceTrace"), false);
	QueryParams.bReturnPhysicalMaterial = false;

	const bool bHit = World->LineTraceSingleByChannel(HitResult, Start, End, TraceChannel, QueryParams);

	if (bHit && HitResult.bBlockingHit)
	{
		OutWorldLocation = HitResult.Location;
		OutSurfaceNormal = HitResult.Normal;
		return true;
	}

	return false;
}

FRotator UBattlematCoordinateMapper::ConvertArucoRotationToUnrealRotator(
	float ArucoRotationGraus,
	float YawOffset,
	bool bInvertYaw
)
{
	float FinalYaw = ArucoRotationGraus;
	if (bInvertYaw)
	{
		FinalYaw = -FinalYaw;
	}

	FinalYaw += YawOffset;
	FinalYaw = FRotator::NormalizeAxis(FinalYaw);

	return FRotator(0.0f, FinalYaw, 0.0f);
}
