# 日志配置模块：统一初始化应用日志，日志文件输出到项目根目录下的 log/ 文件夹
# 支持按天轮转，自动清理过期日志，同时输出到控制台

import logging
import os
from logging.handlers import TimedRotatingFileHandler

# 日志目录：项目根目录/log
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "log")

# 日志格式与级别
LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
LOG_LEVEL = logging.INFO
# 日志保留天数，超过后轮转时自动删除
LOG_BACKUP_DAYS = 90


def make_uvicorn_log_config() -> dict:
    """生成 uvicorn 日志配置：在 uvicorn 默认配置基础上，为访问/错误日志追加文件输出。

    必须通过 uvicorn.run(log_config=...) 传入，
    否则 uvicorn 启动时会用默认配置覆盖已注册的处理器。
    """
    import copy
    from uvicorn.config import LOGGING_CONFIG

    config = copy.deepcopy(LOGGING_CONFIG)
    os.makedirs(LOG_DIR, exist_ok=True)

    def _file_handler(filename: str) -> dict:
        return {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "formatter": "file",
            "level": "INFO",
            "when": "midnight",           # 每天零点轮转
            "backupCount": LOG_BACKUP_DAYS,
            "encoding": "utf-8",          # Windows 下避免中文乱码
            "filename": os.path.join(LOG_DIR, filename),
        }

    config["formatters"]["file"] = {"format": LOG_FORMAT}
    config["handlers"]["app_file"] = _file_handler("uvicorn.log")
    config["handlers"]["access_file"] = _file_handler("uvicorn_access.log")
    config["loggers"]["uvicorn"]["handlers"].append("app_file")
    config["loggers"]["uvicorn.access"]["handlers"].append("access_file")
    return config


def _make_file_handlers(name: str) -> list[logging.Handler]:
    """创建按天轮转的文件处理器，文件名带日期前缀便于归档"""
    os.makedirs(LOG_DIR, exist_ok=True)
    file_path = os.path.join(LOG_DIR, f"{name}.log")
    file_handler = TimedRotatingFileHandler(
        file_path,
        when="midnight",           # 每天零点轮转
        backupCount=LOG_BACKUP_DAYS,
        encoding="utf-8",          # Windows 下避免中文乱码
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    return [file_handler]


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的 logger；首次调用时完成初始化"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(LOG_LEVEL)

        # 控制台输出
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(console_handler)

        # 文件输出（按天轮转）
        for handler in _make_file_handlers("app"):
            logger.addHandler(handler)

        logger.propagate = False
    return logger


if __name__ == "__main__":
    # 模块自检：python logger.py
    test_logger = get_logger("self-test")
    test_logger.info("日志模块自检成功")
    print(f"日志目录: {LOG_DIR}")
