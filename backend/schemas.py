from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Literal, Union, Any
from datetime import datetime, timezone
import uuid

class DimensionScore(BaseModel):
    name: str
    score: float
    reasoning: str

class TrademarkRiskRow(BaseModel):
    likelihood: int
    severity: int
    zone: str 
    commentary: str

class TrademarkRiskMatrix(BaseModel):
    genericness: TrademarkRiskRow
    existing_conflicts: TrademarkRiskRow
    phonetic_similarity: TrademarkRiskRow
    relevant_classes: TrademarkRiskRow
    rebranding_probability: TrademarkRiskRow
    overall_assessment: str

class DomainAnalysis(BaseModel):
    exact_match_status: str
    alternatives: List[Dict[str, str]]
    strategy_note: str

class VisibilityAnalysis(BaseModel):
    google_presence: List[Any] 
    app_store_presence: List[Any]
    warning_triggered: bool
    warning_reason: Optional[str] = None

class CountryAnalysis(BaseModel):
    country: str
    cultural_resonance_score: float
    cultural_notes: str
    linguistic_check: str

class Competitor(BaseModel):
    name: str
    price_axis: str = Field(..., description="X-Axis: Price (Low/Mid/High)")
    modernity_axis: str = Field(..., description="Y-Axis: Modernity (Traditional/Fusion/Modern)")
    quadrant: str = Field(..., description="Quadrant Name")

class CompetitorAnalysis(BaseModel):
    competitors: List[Competitor]
    white_space_analysis: str
    strategic_advantage: str
    suggested_pricing: str

class Recommendation(BaseModel):
    title: str
    content: str

class FinalAssessment(BaseModel):
    verdict_statement: str
    suitability_score: float
    dimension_breakdown: List[Dict[str, float]]
    recommendations: List[Recommendation]
    alternative_path: str

class AlternativeNameSuggestion(BaseModel):
    name: str
    rationale: str

class AlternativeNames(BaseModel):
    poison_words: Optional[List[str]] = Field(default=[], description="Words from original name that caused conflict")
    reasoning: str
    suggestions: List[AlternativeNameSuggestion]

class BrandScore(BaseModel):
    brand_name: str
    namescore: float
    verdict: str 
    summary: str
    strategic_classification: str
    pros: List[str]
    cons: List[str]
    alternative_names: Optional[AlternativeNames] = None
    dimensions: List[DimensionScore]
    trademark_risk: dict 
    trademark_matrix: TrademarkRiskMatrix
    trademark_classes: List[str] = Field(default=[], description="List of Nice Classes")
    domain_analysis: DomainAnalysis
    visibility_analysis: Optional[VisibilityAnalysis] = None
    cultural_analysis: List[CountryAnalysis]
    competitor_analysis: Optional[CompetitorAnalysis] = None
    final_assessment: Optional[FinalAssessment] = None
    positioning_fit: str

class BrandEvaluationRequest(BaseModel):
    brand_names: List[str]
    category: str
    positioning: Literal["Mass", "Premium", "Ultra-Premium"]
    market_scope: Literal["Single Country", "Multi-Country", "Global"]
    countries: List[str]

class BrandEvaluationResponse(BaseModel):
    executive_summary: str
    brand_scores: List[BrandScore]
    # Made optional to prevent validation errors when LLM omits it (e.g. single brand or fatal flaw)
    comparison_verdict: Optional[str] = None 

class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str
