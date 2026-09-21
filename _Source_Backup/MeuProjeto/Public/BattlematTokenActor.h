#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "BattlematTypes.h"
#include "BattlematTokenActor.generated.h"

class USceneComponent;
class UStaticMeshComponent;

/**
 * Ator base projetado diretamente sob cada miniatura física na mesa digital.
 * Gerencia suavização de movimento (Interp), detecção de toque/levantamento e auras visuais.
 */
UCLASS(Blueprintable)
class MEUPROJETO_API ABattlematTokenActor : public AActor
{
	GENERATED_BODY()

public:
	ABattlematTokenActor();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaTime) override;

	/** ID do marcador ArUco */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Battlemat|Token")
	int32 TokenId = 0;

	/** Nome / Identificador do tipo recebido da telemetria */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Battlemat|Token")
	FString TokenType = TEXT("token");

	/** Elemento paranormal (Sangue, Morte, Energia, Conhecimento) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Battlemat|Token")
	EParanormalElement Element = EParanormalElement::None;

	/** Categoria (Investigador, Criatura, NPC) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Battlemat|Token")
	ETokenCategory Category = ETokenCategory::Desconhecido;

	/** Cor temática do token para auras e iluminação dinâmica */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Battlemat|Token")
	FLinearColor ThemeColor = FLinearColor(0.2f, 0.7f, 1.0f, 1.0f);

	/** Raio de visão para revelação da Névoa de Guerra (em unidades Unreal / cm) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Battlemat|Vision")
	float VisionRadius = 350.0f;

	/** Velocidade de interpolação linear (quanto maior, mais ágil o movimento) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Battlemat|Smoothing")
	float LocationInterpSpeed = 14.0f;

	/** Velocidade de interpolação angular */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Battlemat|Smoothing")
	float RotationInterpSpeed = 16.0f;

	/** Tempo limite em segundos sem pacotes para considerar que o jogador levantou a miniatura */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Battlemat|Presence")
	float TimeoutToLift = 1.2f;

	/** Indica se a miniatura está fisicamente sobre o monitor */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Battlemat|Presence")
	bool bIsPhysicallyPresent = true;

	/** Atualiza a pose alvo do token a partir da telemetria */
	UFUNCTION(BlueprintCallable, Category = "Battlemat|Token")
	void UpdateTargetPose(const FVector& NewWorldLocation, const FRotator& NewWorldRotation);

	/** Configura os dados de identidade do token */
	UFUNCTION(BlueprintCallable, Category = "Battlemat|Token")
	void InitializeToken(int32 InTokenId, const FString& InTokenType);

	/** Nome do personagem vinculado vindo da ficha web */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Battlemat|Character")
	FString CharacterName;

	/** Porcentagens de status (0.0 a 1.0) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Battlemat|Character")
	float PVPercent = 1.0f;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Battlemat|Character")
	float SANPercent = 1.0f;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Battlemat|Character")
	float PEPercent = 1.0f;

	/** Atualiza status de PV, Sanidade e PE vindos da ficha web */
	UFUNCTION(BlueprintCallable, Category = "Battlemat|Character")
	void UpdateCharacterStatus(const FString& InName, float InPvPct, float InSanPct, float InPePct, int32 InPvAtual, int32 InPvMax, int32 InSanAtual, int32 InSanMax, int32 InPeAtual, int32 InPeMax);

	/** Dispara efeito de conjuração de ritual sob este token */
	UFUNCTION(BlueprintCallable, Category = "Battlemat|Character")
	void TriggerRitualCast(const FString& RitualName, const FString& InElement, float RangeMeters, int32 PeCost);

protected:
	/** Componente raiz da cena */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Battlemat|Components")
	USceneComponent* SceneRoot;

	/** Mesh da aura no solo diretamente sob a base de 25mm/32mm */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Battlemat|Components")
	UStaticMeshComponent* BaseAuraMesh;

	/** Indicador frontal de orientação da miniatura */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Battlemat|Components")
	UStaticMeshComponent* DirectionMesh;

	/** Evento Blueprint chamado quando o token se move */
	UFUNCTION(BlueprintImplementableEvent, Category = "Battlemat|Events")
	void BP_OnTokenMoved(FVector NewLocation, FRotator NewRotation);

	/** Evento Blueprint chamado quando o jogador levanta a miniatura da mesa */
	UFUNCTION(BlueprintImplementableEvent, Category = "Battlemat|Events")
	void BP_OnTokenLifted();

	/** Evento Blueprint chamado quando a miniatura é pousada novamente */
	UFUNCTION(BlueprintImplementableEvent, Category = "Battlemat|Events")
	void BP_OnTokenPlaced();

	/** Evento Blueprint para atualizar materiais/shaders com a cor do elemento */
	UFUNCTION(BlueprintImplementableEvent, Category = "Battlemat|Events")
	void BP_OnElementVisualsUpdated(EParanormalElement InElement, FLinearColor InThemeColor);

	/** Evento Blueprint quando PV, SAN ou PE são alterados na ficha */
	UFUNCTION(BlueprintImplementableEvent, Category = "Battlemat|Events")
	void BP_OnCharacterStatusUpdated(float InPvPct, float InSanPct, float InPePct);

	/** Evento Blueprint quando um ritual é projetado no chão da mesa */
	UFUNCTION(BlueprintImplementableEvent, Category = "Battlemat|Events")
	void BP_OnRitualCast(const FString& RitualName, const FString& ElementName, float RangeMeters);

private:
	FVector TargetLocation = FVector::ZeroVector;
	FRotator TargetRotation = FRotator::ZeroRotator;
	float TimeSinceLastPacket = 0.0f;
};
