#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Containers/Queue.h"
#include "BattlematTypes.h"
#include "Networking.h"
#include "Common/UdpSocketReceiver.h"
#include "UDPReceiverComponent.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_FourParams(FOnTokenTelemetryReceived, int32, TokenId, const FString&, TokenType, FVector2D, NormalizedPos, float, Rotation);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnFrameTelemetryReceived, const FTokenTelemetryFrame&, Frame);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnRawTelemetryJsonReceived, const FString&, JsonString);

/**
 * Componente que escuta pacotes UDP assincronamente em segundo plano e
 * despacha eventos estruturados no Game Thread para a Unreal Engine.
 */
UCLASS(ClassGroup = (Battlemat), meta = (BlueprintSpawnableComponent))
class MEUPROJETO_API UUDPReceiverComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UUDPReceiverComponent();

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	/** Porta UDP para escutar (padrão do tracker: 8888) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Battlemat|Network")
	int32 Port = 8888;

	/** Iniciar escuta automaticamente no BeginPlay */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Battlemat|Network")
	bool bAutoStart = true;

	/** Inicia o receptor UDP */
	UFUNCTION(BlueprintCallable, Category = "Battlemat|Network")
	bool StartReceiver();

	/** Para o receptor UDP e libera os sockets */
	UFUNCTION(BlueprintCallable, Category = "Battlemat|Network")
	void StopReceiver();

	/** Verifica se o receptor está ativo */
	UFUNCTION(BlueprintPure, Category = "Battlemat|Network")
	bool IsReceiverActive() const;

	/** Evento disparado quando um token individual é atualizado */
	UPROPERTY(BlueprintAssignable, Category = "Battlemat|Events")
	FOnTokenTelemetryReceived OnTokenReceived;

	/** Evento disparado para o frame completo de telemetria */
	UPROPERTY(BlueprintAssignable, Category = "Battlemat|Events")
	FOnFrameTelemetryReceived OnFrameReceived;

	/** Evento de debug contendo o JSON bruto recebido */
	UPROPERTY(BlueprintAssignable, Category = "Battlemat|Events")
	FOnRawTelemetryJsonReceived OnRawJsonReceived;

private:
	void HandleUdpDataReceived(const FArrayReaderPtr& ArrayReaderPtr, const FIPv4Endpoint& Endpoint);
	void ProcessJsonMessage(const FString& JsonString);

	FSocket* ListenSocket = nullptr;
	TUniquePtr<FUdpSocketReceiver> SocketReceiver;

	// Fila thread-safe de mensagens recebidas pelo socket em background
	TQueue<FString, EQueueMode::Mpsc> PendingMessages;
};
