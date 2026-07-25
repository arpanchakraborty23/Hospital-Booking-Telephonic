from dotenv import load_dotenv
from dataclasses import dataclass

from src.utils.main_utils import env, required_env

load_dotenv()


class LiveKitConfig:
    # LiveKit server connection (Cloud injects these as env vars at runtime)
    livekit_url = env("LIVEKIT_URL")
    livekit_api_key = env("LIVEKIT_API_KEY")
    livekit_api_secret = env("LIVEKIT_API_SECRET")
    livekit_agent_name = env("LIVEKIT_AGENT_NAME", "Exia")


class AWSConfig:
    # AWS credentials for S3 recording storage
    aws_access_key = required_env("AWS_ACCESS_KEY_ID")
    aws_secret_key = required_env("AWS_SECRET_ACCESS_KEY")
    aws_region = required_env("AWS_REGION")
    aws_recording_bucket = required_env("AWS_BUCKET_NAME")


class ProviderConfig:
    # Third-party AI provider API keys (all required)
    aws_bedrock_api_key = required_env("AWS_BEDROCK_API_KEY")
    sarvam_api_key = required_env("SARVAM_API_KEY")
    deepgram_api_key = required_env("DEEPGRAM_API_KEY")
    Cartesia_api_key = required_env("CARTESIA_API_KEY")


class DataBaseCOnfig:
    # Database Configuration
    sql_database_url = required_env("NEON_DATABASE_URL")


class EvalConfig:
    # Bedrock model for call evaluation (LLM-based transcript analysis)
    bedrock_eval_model = env("BEDROCK_EVAL_MODEL", "amazon.nova-lite-v1:0")

@dataclass(frozen=True)
class Credentials:
    # Aggregates all config classes for single import point
    livekit: type[LiveKitConfig] = LiveKitConfig
    aws: type[AWSConfig] = AWSConfig
    providers: type[ProviderConfig] = ProviderConfig
    database: type[DataBaseCOnfig] = DataBaseCOnfig
    eval: type[EvalConfig] = EvalConfig
  