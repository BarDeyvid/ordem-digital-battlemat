#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "BattlematTypes.generated.h"

/**
 * Elementos paranormais do universo de Ordem Paranormal RPG.
 */
UENUM(BlueprintType)
enum class EParanormalElement : uint8
{
	None			UMETA(DisplayName = "Nenhum"),
	Sangue			UMETA(DisplayName = "Sangue"),
	Morte			UMETA(DisplayName = "Morte"),
	Energia			UMETA(DisplayName = "Energia"),
	Conhecimento	UMETA(DisplayName = "Conhecimento"),
	Medo			UMETA(DisplayName = "Medo")
};

/**
 * Categoria funcional do token na mesa.
 */
UENUM(BlueprintType)
enum class ETokenCategory : uint8
{
	Investigador	UMETA(DisplayName = "Investigador"),
	Criatura		UMETA(DisplayName = "Criatura"),
	NPC				UMETA(DisplayName = "NPC"),
	Objeto			UMETA(DisplayName = "Objeto"),
	Desconhecido	UMETA(DisplayName = "Desconhecido")
};

/**
 * Dados de um token individual recebidos no pacote de telemetria.
 */
USTRUCT(BlueprintType)
struct MEUPROJETO_API FTokenTelemetryItem
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Battlemat|Token")
	int32 Id = 0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Battlemat|Token")
	FString Type = TEXT("token");

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Battlemat|Token")
	FVector2D NormalizedPos = FVector2D::ZeroVector;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Battlemat|Token")
	float Rotation = 0.0f;
};

/**
 * Frame completo de telemetria recebido via UDP.
 */
USTRUCT(BlueprintType)
struct MEUPROJETO_API FTokenTelemetryFrame
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Battlemat|Telemetry")
	double Timestamp = 0.0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Battlemat|Telemetry")
	TArray<FTokenTelemetryItem> Tokens;
};

/**
 * Utilitários estáticos para tipos e elementos paranormais.
 */
UCLASS()
class MEUPROJETO_API UParanormalTypeUtils : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	UFUNCTION(BlueprintPure, Category = "Battlemat|Types")
	static EParanormalElement ParseElementFromType(const FString& InType)
	{
		if (InType.Contains(TEXT("sangue"), ESearchCase::IgnoreCase)) return EParanormalElement::Sangue;
		if (InType.Contains(TEXT("morte"), ESearchCase::IgnoreCase)) return EParanormalElement::Morte;
		if (InType.Contains(TEXT("energia"), ESearchCase::IgnoreCase)) return EParanormalElement::Energia;
		if (InType.Contains(TEXT("conhecimento"), ESearchCase::IgnoreCase)) return EParanormalElement::Conhecimento;
		if (InType.Contains(TEXT("medo"), ESearchCase::IgnoreCase)) return EParanormalElement::Medo;
		return EParanormalElement::None;
	}

	UFUNCTION(BlueprintPure, Category = "Battlemat|Types")
	static ETokenCategory ParseCategoryFromType(const FString& InType)
	{
		if (InType.Contains(TEXT("investigador"), ESearchCase::IgnoreCase)) return ETokenCategory::Investigador;
		if (InType.Contains(TEXT("criatura"), ESearchCase::IgnoreCase)) return ETokenCategory::Criatura;
		if (InType.Contains(TEXT("npc"), ESearchCase::IgnoreCase)) return ETokenCategory::NPC;
		if (InType.Contains(TEXT("objeto"), ESearchCase::IgnoreCase)) return ETokenCategory::Objeto;
		return ETokenCategory::Desconhecido;
	}

	UFUNCTION(BlueprintPure, Category = "Battlemat|Types")
	static FLinearColor GetElementThemeColor(EParanormalElement InElement)
	{
		switch (InElement)
		{
		case EParanormalElement::Sangue:
			return FLinearColor(0.85f, 0.05f, 0.05f, 1.0f); // Vermelho carmesim
		case EParanormalElement::Morte:
			return FLinearColor(0.12f, 0.12f, 0.14f, 1.0f); // Lodo negro/cinza
		case EParanormalElement::Energia:
			return FLinearColor(0.95f, 0.08f, 0.85f, 1.0f); // Magenta/Roxo elétrico
		case EParanormalElement::Conhecimento:
			return FLinearColor(0.98f, 0.82f, 0.12f, 1.0f); // Ouro/Âmbar
		case EParanormalElement::Medo:
			return FLinearColor(0.85f, 0.85f, 0.95f, 1.0f); // Branco espectral
		default:
			return FLinearColor(0.2f, 0.7f, 1.0f, 1.0f);    // Ciano padrão para investigadores
		}
	}
};
