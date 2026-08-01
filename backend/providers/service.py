import logging
import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from backend.providers.schemas import LLMRequest, LLMResponse
from backend.providers.factory import ProviderFactory
from backend.providers.registry import ProviderRegistry
from backend.providers.pricing import PricingManager
from backend.providers.tokenizer import Tokenizer
from backend.providers.retry import RetryHandler
from backend.providers.validators import RequestValidator
from backend.providers.models import Provider as DBProvider, Model as DBModel, ProviderRequest as DBProviderRequest
from backend.providers.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

class ProviderService:
    def __init__(self, pricing_cache_path: Optional[str] = None):
        self.registry = ProviderRegistry()
        self.factory = ProviderFactory(self.registry)
        self.pricing_manager = PricingManager(pricing_cache_path)
        self.tokenizer = Tokenizer()

    def generate(self, db: Session, request: LLMRequest, timeout: int = 120) -> LLMResponse:
        """
        Executes a prompt generation request, standardizes the response, calculates cost,
        applies retry policies, and logs execution parameters into the database.
        """
        RequestValidator.validate_request(request)
        
        provider_name = request.provider.lower()
        
        # Load provider from database, or auto-seed if missing
        db_provider = db.query(DBProvider).filter(DBProvider.id == provider_name).first()
        if not db_provider:
            db_provider = DBProvider(
                id=provider_name,
                provider_name=request.provider,
                enabled=True
            )
            db.add(db_provider)
            db.commit()
            db.refresh(db_provider)
            
        if not db_provider.enabled:
            raise ConfigurationError(f"Provider '{request.provider}' is currently disabled in the database.")
            
        api_base = db_provider.api_base
        
        provider_instance = self.factory.get_provider(
            provider_name=provider_name,
            api_base=api_base
        )
        
        def execute_inference():
            return provider_instance.generate(request, timeout=timeout)
            
        try:
            response: LLMResponse = RetryHandler.execute_with_retry(
                execute_inference,
                max_retries=3,
                initial_backoff=2.0
            )
            
            # Calculate cost
            cost = self.pricing_manager.calculate_price(
                provider=provider_name,
                model=request.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens
            )
            response.estimated_cost = cost
            
            # Log execution to DB
            db_request = DBProviderRequest(
                experiment_run=request.experiment_id,
                provider=provider_name,
                model=request.model,
                latency=response.latency_ms,
                tokens=response.total_tokens,
                cost=cost,
                status="success",
                created_at=response.request_timestamp
            )
            db.add(db_request)
            db.commit()
            
            return response
            
        except Exception as e:
            # Log failed request to database
            db_request = DBProviderRequest(
                experiment_run=request.experiment_id,
                provider=provider_name,
                model=request.model,
                latency=0,
                tokens=0,
                cost=0.0,
                status="failed",
                created_at=datetime.datetime.utcnow()
            )
            db.add(db_request)
            db.commit()
            
            # Do NOT write prompt contents to application logs
            logger.error(
                f"LLM request execution failed. "
                f"Provider: {provider_name}, Model: {request.model}, Error: {str(e)}"
            )
            raise e

    def list_models(self, db: Session, provider_id: Optional[str] = None) -> List[DBModel]:
        """
        Synchronizes models from active providers and returns available models from the DB.
        """
        self._ensure_providers_seeded(db)
        
        query = db.query(DBProvider)
        if provider_id:
            query = query.filter(DBProvider.id == provider_id.lower())
        providers = query.all()
        
        for p in providers:
            if not p.enabled:
                continue
            try:
                provider_instance = self.factory.get_provider(provider_name=p.id, api_base=p.api_base)
                model_meta_list = provider_instance.list_models()
                
                for mm in model_meta_list:
                    model_name = mm["model_name"]
                    db_model = db.query(DBModel).filter(
                        DBModel.provider_id == p.id,
                        DBModel.model_name == model_name
                    ).first()
                    
                    if db_model:
                        db_model.context_window = mm.get("context_window", db_model.context_window)
                        db_model.supports_seed = mm.get("supports_seed", db_model.supports_seed)
                        db_model.supports_temperature = mm.get("supports_temperature", db_model.supports_temperature)
                        db_model.supports_top_p = mm.get("supports_top_p", db_model.supports_top_p)
                        db_model.supports_json_mode = mm.get("supports_json_mode", db_model.supports_json_mode)
                        db_model.status = mm.get("status", "active")
                    else:
                        db_model = DBModel(
                            provider_id=p.id,
                            model_name=model_name,
                            context_window=mm.get("context_window"),
                            supports_seed=mm.get("supports_seed", True),
                            supports_temperature=mm.get("supports_temperature", True),
                            supports_top_p=mm.get("supports_top_p", True),
                            supports_json_mode=mm.get("supports_json_mode", True),
                            status="active"
                        )
                        db.add(db_model)
                db.commit()
            except Exception as e:
                logger.warning(f"Could not list or sync models for provider '{p.id}': {e}")
                
        res_query = db.query(DBModel).join(DBProvider).filter(DBProvider.enabled == True, DBModel.status == "active")
        if provider_id:
            res_query = res_query.filter(DBModel.provider_id == provider_id.lower())
        return res_query.all()

    def health_check(self, db: Session, provider_id: str) -> bool:
        provider_id = provider_id.lower()
        db_provider = db.query(DBProvider).filter(DBProvider.id == provider_id).first()
        if not db_provider or not db_provider.enabled:
            return False
            
        try:
            provider_instance = self.factory.get_provider(
                provider_name=provider_id,
                api_base=db_provider.api_base
            )
            return provider_instance.health_check()
        except Exception:
            return False

    def estimate_cost(self, provider_id: str, model_name: str, input_tokens: int, output_tokens: int) -> float:
        return self.pricing_manager.calculate_price(provider_id, model_name, input_tokens, output_tokens)

    def estimate_tokens(self, text: str, provider_id: Optional[str] = None, model_name: Optional[str] = None) -> int:
        return self.tokenizer.estimate_tokens(text, model_name)

    def calculate_price(self, provider_id: str, model_name: str, input_tokens: int, output_tokens: int) -> float:
        return self.pricing_manager.calculate_price(provider_id, model_name, input_tokens, output_tokens)

    def _ensure_providers_seeded(self, db: Session) -> None:
        defaults = [
            ("gemini", "Google Gemini", True, None),
            ("openai", "OpenAI", True, None),
            ("openrouter", "OpenRouter", True, None),
            ("ollama", "Ollama", True, "http://localhost:11434")
        ]
        
        changed = False
        for pid, pname, enabled, base in defaults:
            p = db.query(DBProvider).filter(DBProvider.id == pid).first()
            if not p:
                p = DBProvider(
                    id=pid,
                    provider_name=pname,
                    enabled=enabled,
                    api_base=base
                )
                db.add(p)
                changed = True
        if changed:
            db.commit()
