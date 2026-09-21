#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "Engine/World.h"
#include "CollisionQueryParams.h"
#include "BattlematCoordinateMapper.generated.h"

/**
 * Biblioteca de funções matemáticas e físicas para projetar coordenadas normalizadas 2D (0..1)
 * da câmera/monitor deitado sobre o chão e relevo de mapas 3D no Unreal Engine.
 */
UCLASS()
class MEUPROJETO_API UBattlematCoordinateMapper : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * Mapeia coordenadas normalizadas (0.0 a 1.0) para uma posição no mundo 3D através de raycast vertical (Line Trace).
	 * Garante que a base do token acompanhe perfeitamente desníveis de terreno, mesas e escadas.
	 *
	 * @param WorldContextObject Objeto de contexto do mundo (Self no Blueprint)
	 * @param NormalizedPos Coordenadas (X, Y) normalizadas de 0.0 a 1.0 vindas do tracker
	 * @param PlayAreaOrigin Centro da área tática da mesa no mundo Unreal
	 * @param PlayAreaExtent Extensão (tamanho da metade) da mesa nos eixos X e Y
	 * @param TraceHeightStart Altura superior de início do raio de colisão (ex: +1500 cm)
	 * @param TraceHeightEnd Altura inferior de término do raio (ex: -500 cm)
	 * @param TraceChannel Canal de colisão do chão (padrão: ECC_Visibility)
	 * @param OutWorldLocation Posição 3D calculada sobre a superfície
	 * @param OutSurfaceNormal Normal da superfície colidida (útil para alinhar efeitos ao chão)
	 * @return Verdadeiro se o raio encontrou uma superfície sólida
	 */
	UFUNCTION(BlueprintCallable, Category = "Battlemat|Coordinates", meta = (WorldContext = "WorldContextObject"))
	static bool MapNormalizedToWorldSurface(
		const UObject* WorldContextObject,
		FVector2D NormalizedPos,
		FVector PlayAreaOrigin,
		FVector2D PlayAreaExtent,
		float TraceHeightStart,
		float TraceHeightEnd,
		ECollisionChannel TraceChannel,
		FVector& OutWorldLocation,
		FVector& OutSurfaceNormal
	);

	/**
	 * Converte a rotação em graus (0 a 360) enviada pelo ArUco para um FRotator do Unreal Engine.
	 *
	 * @param ArucoRotationGraus Rotação do marcador em graus
	 * @param YawOffset Compensação angular de calibração (ajusta a orientação física da câmera/monitor)
	 * @param bInvertYaw Se a rotação deve ser invertida no sentido horário
	 * @return FRotator pronto para aplicar ao Actor do token
	 */
	UFUNCTION(BlueprintPure, Category = "Battlemat|Coordinates")
	static FRotator ConvertArucoRotationToUnrealRotator(
		float ArucoRotationGraus,
		float YawOffset = 0.0f,
		bool bInvertYaw = false
	);
};
