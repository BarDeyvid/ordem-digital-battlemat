#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "BattlematTypes.h"
#include "BattlematTokenActor.h"
#include "UDPReceiverComponent.h"
#include "BattlematManagerActor.generated.h"

class UBoxComponent;

/**
 * Ator central de controle da mesa de batalha digital (Battlemat Manager).
 * Recebe pacotes UDP, converte coordenadas para o mapa 3D e gerencia o ciclo de vida dos tokens.
 */
UCLASS(Blueprintable)
class MEUPROJETO_API ABattlematManagerActor : public AActor
{
	GENERATED_BODY()

public:
	ABattlematManagerActor();

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	/** Componente receptor de pacotes UDP na porta 8888 */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Battlemat|Network")
	UUDPReceiverComponent* UdpReceiver;

	/** Caixa que delimita visualmente e fisicamente a área útil da mesa no mundo 3D */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Battlemat|Bounds")
	UBoxComponent* TableBounds;

	/** Classe do ator de token a ser instanciada (pode ser substituída por Blueprints personalizados) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Battlemat|Spawning")
	TSubclassOf<ABattlematTokenActor> DefaultTokenClass;

	/** Ajuste angular de calibração para alinhar a orientação da câmera com o mundo da Unreal */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Battlemat|Calibration")
	float YawOffset = 0.0f;

	/** Inverter sentido horário da rotação */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Battlemat|Calibration")
	bool bInvertRotation = false;

	/** Nível de degradação da Membrana (0: Intacta, 1: Instável, 2: Danificada, 3: Ruptura) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Battlemat|OrdemParanormal", meta = (ClampMin = "0", ClampMax = "3"))
	int32 MembranaLevel = 0;

	/** Altera o estado da Membrana e dispara efeitos no mapa */
	UFUNCTION(BlueprintCallable, Category = "Battlemat|OrdemParanormal")
	void SetMembranaLevel(int32 NewLevel);

	/** Obtém o token ativo pelo ID do marcador ArUco */
	UFUNCTION(BlueprintPure, Category = "Battlemat|Tokens")
	ABattlematTokenActor* GetTokenById(int32 TokenId) const;

	/** Lista de todos os tokens atualmente spawnados */
	UFUNCTION(BlueprintPure, Category = "Battlemat|Tokens")
	TArray<ABattlematTokenActor*> GetAllActiveTokens() const;

protected:
	/** Callback disparado quando o UUDPReceiverComponent recebe dados de um token */
	UFUNCTION()
	void HandleTokenTelemetry(int32 TokenId, const FString& TokenType, FVector2D NormalizedPos, float Rotation);

	/** Evento Blueprint disparado quando um novo token é inserido na mesa */
	UFUNCTION(BlueprintImplementableEvent, Category = "Battlemat|Events")
	void BP_OnTokenSpawned(ABattlematTokenActor* TokenActor);

	/** Evento Blueprint disparado quando o nível da membrana é alterado */
	UFUNCTION(BlueprintImplementableEvent, Category = "Battlemat|Events")
	void BP_OnMembranaStateChanged(int32 NewMembranaLevel);

private:
	UPROPERTY()
	TMap<int32, ABattlematTokenActor*> ActiveTokens;
};
