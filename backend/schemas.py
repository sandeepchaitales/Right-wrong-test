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
    risk_level: Optional[str] = Field(default="LOW", description="LOW/MEDIUM/HIGH - .com alone = LOW risk")
    has_active_business: Optional[str] = Field(default="UNKNOWN", description="Is there an operating business?")
    has_trademark: Optional[str] = Field(default="UNKNOWN", description="Is there a registered TM?")
    alternatives: List[Dict[str, str]]
    strategy_note: str
    score_impact: Optional[str] = Field(default="-1 point max for taken .com", description="Score impact explanation")

class DomainCheckResult(BaseModel):
    domain: str
    status: str
    available: Optional[bool] = None

class MultiDomainAvailability(BaseModel):
    category_domains: List[DomainCheckResult] = Field(default=[], description="Category-specific TLDs like .shop, .tech")
    country_domains: List[DomainCheckResult] = Field(default=[], description="Country-specific TLDs like .in, .co.uk")
    recommended_domain: Optional[str] = None
    acquisition_strategy: Optional[str] = None

class SocialHandleResult(BaseModel):
    platform: str
    handle: str
    status: str
    available: Optional[bool] = None

class SocialAvailability(BaseModel):
    handle: str
    platforms: List[SocialHandleResult] = Field(default=[], description="Social platform availability")
    available_platforms: List[str] = Field(default=[], description="List of available platforms")
    taken_platforms: List[str] = Field(default=[], description="List of taken platforms")
    recommendation: Optional[str] = None

class ConflictItem(BaseModel):
    name: str
    category: str
    their_customer_avatar: Optional[str] = Field(default=None, description="Who uses this competitor/app")
    customer_overlap: Optional[str] = Field(default=None, description="HIGH/NONE - overlap with user's customers")
    risk_level: str = Field(default="LOW", description="HIGH for direct competitors with same customers, LOW for name twins")
    reason: Optional[str] = None

class VisibilityAnalysis(BaseModel):
    user_customer_avatar: Optional[str] = Field(default=None, description="Who buys the user's product")
    direct_competitors: List[ConflictItem] = Field(default=[], description="Same industry + same customers - HIGH risk")
    name_twins: List[ConflictItem] = Field(default=[], description="Different industry OR different customers - LOW risk, NOT rejection factors")
    google_presence: List[Any] 
    app_store_presence: List[Any]
    warning_triggered: bool
    warning_reason: Optional[str] = None
    conflict_summary: Optional[str] = Field(default=None, description="Summary of customer avatar analysis")

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
    multi_domain_availability: Optional[MultiDomainAvailability] = None
    social_availability: Optional[SocialAvailability] = None
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
