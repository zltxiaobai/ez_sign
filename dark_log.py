from loguru import logger
import os
import sys
from datetime import datetime
import traceback
import inspect


class DarkLog:
    """
    功能描述: 基于loguru的增强日志记录器，支持多实例、ID绑定和控制台输出控制
    参数: 无
    返回值: 无
    异常描述: 无
    调用演示:
        # 创建两个不同ID的日志实例
        logger1 = CustomLogger("user123")
        logger2 = CustomLogger("admin456")

        # 记录不同级别的日志
        logger1.info("这是信息日志") #默认打印
        logger2.warning("这是警告日志")

        # 控制控制台输出
        logger1.set_console_output(False)
        logger1.info("此消息不会显示在控制台")


        # 在控制台打印错误
        logger.exception(f"索引越界错误: {str(e)}")
        logger.log_exception(message=f"索引越界错误: {str(e)}")

        # 不打印错误
        logger.exception(f"索引越界错误A: {str(e)}",False) 显示错误，但是不显示详细信息
        2025-06-04 17:44:17.565 | ERROR    | dark_log.py:exception:180 | ID: exception_test | 索引越界错误: list index out of range
        直接不显示，在日志显示
        logger.log_exception(message=f"索引越界错误: {str(e)}", show_console=False)
    """

    def __init__(self, id_value):
        """
        功能描述: 初始化自定义日志记录器
        参数:
            id_value: 日志实例的唯一标识符，将显示在每条日志记录中
        返回值: 无
        异常描述: 无
        调用演示:
            logger = CustomLogger("user123")
        """
        self.id = id_value
        self.console_output = True

        # 确保文件夹存在
        os.makedirs("log_", exist_ok=True)


        # 移除所有已存在的处理器，避免重复输出
        # 这一步非常关键，确保每次创建CustomLogger实例时，都从一个干净的logger状态开始
        logger.remove()

        # 添加文件处理器，按天轮换
        log_file = os.path.join("log_", "{time:YYYY-MM-DD}.log")
        self.file_handler_id = logger.add(
            log_file,
            rotation="00:00",  # 每天午夜轮换
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{extra[user_script]}</cyan>:<cyan>{extra[user_function]}</cyan>:<cyan>{extra[user_line]}</cyan> | <magenta>ID: {extra[id]}</magenta> - <level>{message}</level>",
            enqueue=True,
            diagnose=True,
            backtrace=True,
            level="INFO"
        )

        # 添加控制台处理器
        self.console_handler_id = None
        if self.console_output:
            self._add_console_handler()

        # 创建带有id的上下文logger
        self.logger = logger.bind(id=self.id)

    def _add_console_handler(self):
        """添加控制台处理器"""
        # 只有当console_handler_id为None时才添加，避免重复添加
        if self.console_handler_id is not None:
            return

        self.console_handler_id = logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{extra[user_script]}</cyan>:<cyan>{extra[user_function]}</cyan>:<cyan>{extra[user_line]}</cyan> | <magenta>ID: {extra[id]}</magenta> - <level>{message}</level>",
            enqueue=True,
            diagnose=True,
            backtrace=True,
            level="INFO"
        )

    def _remove_console_handler(self):
        """移除控制台处理器"""
        if self.console_handler_id is not None:
            try:
                logger.remove(self.console_handler_id)
            except ValueError:
                # 如果处理器已经被移除，忽略错误
                pass
            finally:
                self.console_handler_id = None

    def set_console_output(self, enabled):
        """
        功能描述: 控制是否在控制台输出日志
        参数:
            enabled: 布尔值，True表示启用控制台输出，False表示禁用
        返回值: 无
        异常描述: 无
        调用演示:
            logger.set_console_output(False)  # 禁用控制台输出
            logger.set_console_output(True)   # 启用控制台输出
        """
        if enabled and not self.console_output:
            self._add_console_handler()
            self.console_output = True
        elif not enabled and self.console_output:
            self._remove_console_handler()
            self.console_output = False

    def _log_with_console_control(self, level_method, message, show_console=None):
        """
        功能描述: 使用控制台控制选项记录日志
        参数:
            level_method: 日志级别方法（如 logger.info, logger.error 等）
            message: 要记录的日志消息
            show_console: 是否在控制台显示此条日志
        返回值: 无
        异常描述: 无
        调用演示: 内部方法，不直接调用
        """
        # 获取当前运行的脚本名、函数名和行号
        frame = inspect.currentframe()
        user_script = "unknown"
        user_function = "unknown"
        user_line = 0

        try:
            frames = inspect.getouterframes(frame)
            for f in frames:
                if not f.filename.endswith('dark_log.py'):
                    user_script = os.path.basename(f.filename)
                    user_function = f.function
                    user_line = f.lineno
                    break
        finally:
            del frame

        # 绑定额外的上下文信息
        context_logger = self.logger.bind(
            user_script=user_script,
            user_function=user_function,
            user_line=user_line
        )

        # 原有的控制台输出控制逻辑
        original_state = self.console_output
        temp_change = False

        if show_console is not None and show_console != self.console_output:
            # 临时改变控制台输出状态
            self.set_console_output(show_console)
            temp_change = True

        # 记录日志
        # 使用getattr来动态调用绑定了额外信息的logger的相应级别方法
        # 这里不需要再通过level_method.__name__来获取方法名，直接调用即可
        getattr(context_logger, level_method.__name__)(message)

        # 如果临时改变了状态，恢复原来的状态
        if temp_change:
            self.set_console_output(original_state)

    def debug(self, message, show_console=None):
        # 传递原始的logger方法，而不是绑定后的方法
        self._log_with_console_control(self.logger.debug, message, show_console)

    def info(self, message, show_console=None):
        # 传递原始的logger方法，而不是绑定后的方法
        self._log_with_console_control(self.logger.info, message, show_console)

    def warning(self, message, show_console=None):
        # 传递原始的logger方法，而不是绑定后的方法
        self._log_with_console_control(self.logger.warning, message, show_console)

    def error(self, message, show_console=None):
        # 传递原始的logger方法，而不是绑定后的方法
        self._log_with_console_control(self.logger.error, message, show_console)

    def critical(self, message, show_console=None):
        # 传递原始的logger方法，而不是绑定后的方法
        self._log_with_console_control(self.logger.critical, message, show_console)

    def exception(self, message, exc_info=True, show_console=None):
        """
        功能描述: 记录异常详细信息，包括堆栈跟踪
        参数:
            message: 异常信息描述
            exc_info: 是否包含异常详细信息，默认为True
            show_console: 是否在控制台显示，None表示使用当前设置
        返回值: 无
        异常描述: 无
        调用演示:
            try:
                result = 10 / 0  # 除零错误
            except Exception as e:
                logger.exception(f"除零错误: {str(e)}")
                logger.exception(f"不在控制台显示的错误", True, False)
        """
        # 保存原始状态
        original_state = self.console_output
        temp_change = False

        if show_console is not None and show_console != self.console_output:
            # 临时改变控制台输出状态
            self.set_console_output(show_console)
            temp_change = True

        # 记录异常信息
        if exc_info:
            # 同样需要绑定额外信息
            frame = inspect.currentframe()
            user_script = "unknown"
            user_function = "unknown"
            user_line = 0
            try:
                frames = inspect.getouterframes(frame)
                for f in frames:
                    if not f.filename.endswith('dark_log.py'):
                        user_script = os.path.basename(f.filename)
                        user_function = f.function
                        user_line = f.lineno
                        break
            finally:
                del frame

            context_logger = self.logger.bind(
                user_script=user_script,
                user_function=user_function,
                user_line=user_line
            )
            context_logger.exception(message)
        else:
            # 这里也应该使用绑定了额外信息的logger，或者确保extra信息被传递
            # 如果不使用context_logger，那么extra信息将不会被添加到日志中
            # 考虑到exception方法通常用于记录异常，我们应该确保它也包含user_script等信息
            frame = inspect.currentframe()
            user_script = "unknown"
            user_function = "unknown"
            user_line = 0
            try:
                frames = inspect.getouterframes(frame)
                for f in frames:
                    if not f.filename.endswith('dark_log.py'):
                        user_script = os.path.basename(f.filename)
                        user_function = f.function
                        user_line = f.lineno
                        break
            finally:
                del frame

            context_logger = self.logger.bind(
                user_script=user_script,
                user_function=user_function,
                user_line=user_line
            )
            context_logger.error(message)

        # 恢复原始状态
        if temp_change:
            self.set_console_output(original_state)

    def log_exception(self, message="发生异常", show_console=None, exc_type=None, exc_value=None, exc_traceback=None):
        """记录自定义异常详细信息

        Args:
            exc_type: 异常类型，默认为None（使用sys.exc_info获取）
            exc_value: 异常值，默认为None（使用sys.exc_info获取）
            exc_traceback: 异常堆栈，默认为None（使用sys.exc_info获取）
            message: 异常信息描述
            show_console: 是否在控制台显示，None表示使用当前设置
        """
        # 保存原始状态
        original_state = self.console_output
        temp_change = False

        if show_console is not None and show_console != self.console_output:
            # 临时改变控制台输出状态
            self.set_console_output(show_console)
            temp_change = True

        # 如果没有提供异常信息，则使用sys.exc_info获取当前异常
        if exc_type is None or exc_value is None or exc_traceback is None:
            exc_info = sys.exc_info()
            if exc_type is None:
                exc_type = exc_info[0]
            if exc_value is None:
                exc_value = exc_info[1]
            if exc_traceback is None:
                exc_traceback = exc_info[2]

        # 格式化异常信息
        if exc_type and exc_value and exc_traceback:
            exception_details = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            full_message = f"{message}\n{exception_details}"
            # 同样需要绑定额外信息
            frame = inspect.currentframe()
            user_script = "unknown"
            user_function = "unknown"
            user_line = 0
            try:
                frames = inspect.getouterframes(frame)
                for f in frames:
                    if not f.filename.endswith('dark_log.py'):
                        user_script = os.path.basename(f.filename)
                        user_function = f.function
                        user_line = f.lineno
                        break
            finally:
                del frame

            context_logger = self.logger.bind(
                user_script=user_script,
                user_function=user_function,
                user_line=user_line
            )
            context_logger.error(full_message)
        else:
            # 同样，这里也应该使用绑定了额外信息的logger
            frame = inspect.currentframe()
            user_script = "unknown"
            user_function = "unknown"
            user_line = 0
            try:
                frames = inspect.getouterframes(frame)
                for f in frames:
                    if not f.filename.endswith('dark_log.py'):
                        user_script = os.path.basename(f.filename)
                        user_function = f.function
                        user_line = f.lineno
                        break
            finally:
                del frame

            context_logger = self.logger.bind(
                user_script=user_script,
                user_function=user_function,
                user_line=user_line
            )
            context_logger.error(message)

        # 恢复原始状态
        if temp_change:
            self.set_console_output(original_state)
