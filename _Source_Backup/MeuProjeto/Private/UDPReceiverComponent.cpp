#include "UDPReceiverComponent.h"
#include "Common/UdpSocketBuilder.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonReader.h"
#include "JsonObjectConverter.h"

UUDPReceiverComponent::UUDPReceiverComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickInterval = 0.0f; // Executa todo frame
}

void UUDPReceiverComponent::BeginPlay()
{
	Super::BeginPlay();

	if (bAutoStart)
	{
		StartReceiver();
	}
}

void UUDPReceiverComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	StopReceiver();
	Super::EndPlay(EndPlayReason);
}

bool UUDPReceiverComponent::StartReceiver()
{
	if (IsReceiverActive())
	{
		return true;
	}

	FIPv4Endpoint Endpoint(FIPv4Address::Any, Port);

	ListenSocket = FUdpSocketBuilder(TEXT("BattlematUdpSocket"))
		.AsReusable()
		.AsNonBlocking()
		.BoundToEndpoint(Endpoint)
		.WithReceiveBufferSize(2 * 1024 * 1024);

	if (!ListenSocket)
	{
		UE_LOG(LogTemp, Error, TEXT("[Battlemat UDP] Falha ao criar e vincular socket na porta %d"), Port);
		return false;
	}

	SocketReceiver = MakeUnique<FUdpSocketReceiver>(
		ListenSocket,
		FTimespan::FromMilliseconds(100),
		TEXT("BattlematUdpReceiverThread")
	);

	SocketReceiver->OnDataReceived().BindUObject(this, &UUDPReceiverComponent::HandleUdpDataReceived);
	SocketReceiver->Start();

	UE_LOG(LogTemp, Log, TEXT("[Battlemat UDP] Escutando telemetria na porta %d com sucesso!"), Port);
	return true;
}

void UUDPReceiverComponent::StopReceiver()
{
	if (SocketReceiver)
	{
		SocketReceiver->Stop();
		SocketReceiver.Reset();
	}

	if (ListenSocket)
	{
		ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(ListenSocket);
		ListenSocket = nullptr;
	}

	UE_LOG(LogTemp, Log, TEXT("[Battlemat UDP] Receptor encerrado."));
}

bool UUDPReceiverComponent::IsReceiverActive() const
{
	return ListenSocket != nullptr && SocketReceiver.IsValid();
}

void UUDPReceiverComponent::HandleUdpDataReceived(const FArrayReaderPtr& ArrayReaderPtr, const FIPv4Endpoint& Endpoint)
{
	if (!ArrayReaderPtr.IsValid() || ArrayReaderPtr->Num() == 0)
	{
		return;
	}

	// Converte bytes brutos em string UTF-8
	FString ReceivedString;
	ReceivedString.Empty(ArrayReaderPtr->Num());

	const ANSICHAR* DataPtr = reinterpret_cast<const ANSICHAR*>(ArrayReaderPtr->GetData());
	FUTF8ToTCHAR Converted(DataPtr, ArrayReaderPtr->Num());
	ReceivedString.AppendChars(Converted.Get(), Converted.Length());

	// Enfileira de forma thread-safe para ser consumido no Game Thread
	PendingMessages.Enqueue(ReceivedString);
}

void UUDPReceiverComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

	// Processa mensagens pendentes no Game Thread
	FString Message;
	while (PendingMessages.Dequeue(Message))
	{
		ProcessJsonMessage(Message);
	}
}

void UUDPReceiverComponent::ProcessJsonMessage(const FString& JsonString)
{
	OnRawJsonReceived.Broadcast(JsonString);

	TSharedPtr<FJsonObject> JsonObject;
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonString);

	if (!FJsonSerializer::Deserialize(Reader, JsonObject) || !JsonObject.IsValid())
	{
		return;
	}

	FTokenTelemetryFrame Frame;
	Frame.Timestamp = JsonObject->GetNumberField(TEXT("timestamp"));

	const TArray<TSharedPtr<FJsonValue>>* TokensArrayJson;
	if (JsonObject->TryGetArrayField(TEXT("tokens"), TokensArrayJson) && TokensArrayJson)
	{
		for (const TSharedPtr<FJsonValue>& TokenVal : *TokensArrayJson)
		{
			TSharedPtr<FJsonObject> TokenObj = TokenVal->AsObject();
			if (!TokenObj.IsValid())
			{
				continue;
			}

			FTokenTelemetryItem Item;
			Item.Id = TokenObj->GetIntegerField(TEXT("id"));
			Item.Type = TokenObj->GetStringField(TEXT("type"));

			double X = 0.0;
			double Y = 0.0;
			TokenObj->TryGetNumberField(TEXT("x"), X);
			TokenObj->TryGetNumberField(TEXT("y"), Y);
			Item.NormalizedPos = FVector2D(X, Y);

			double Rot = 0.0;
			TokenObj->TryGetNumberField(TEXT("rotation"), Rot);
			Item.Rotation = static_cast<float>(Rot);

			Frame.Tokens.Add(Item);

			// Dispara evento individual por token
			OnTokenReceived.Broadcast(Item.Id, Item.Type, Item.NormalizedPos, Item.Rotation);
		}
	}

	// Dispara evento do frame completo
	OnFrameReceived.Broadcast(Frame);
}
