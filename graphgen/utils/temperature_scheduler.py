"""
Temperature scheduler for dynamic temperature adjustment during generation.
"""


class TemperatureScheduler:
    """
    Scheduler for dynamically adjusting temperature during QA generation.
    Supports linear decay, exponential decay, and custom schedules.
    """
    
    def __init__(
        self,
        initial_temp: float = 1.0,
        final_temp: float = 0.3,
        decay_type: str = "exponential",
        decay_rate: float = 0.1,
        total_steps: int = 100,
    ):
        """
        Initialize temperature scheduler.
        
        :param initial_temp: Initial temperature value
        :param final_temp: Final temperature value
        :param decay_type: Type of decay ('linear', 'exponential', 'cosine')
        :param decay_rate: Decay rate (for exponential decay)
        :param total_steps: Total number of steps for scheduling
        """
        self.initial_temp = initial_temp
        self.final_temp = final_temp
        self.decay_type = decay_type
        self.decay_rate = decay_rate
        self.total_steps = total_steps
        self.current_step = 0
    
    def get_temperature(self) -> float:
        """
        Get current temperature based on schedule.
        
        :return: Current temperature value
        """
        if self.current_step >= self.total_steps:
            return self.final_temp
        
        progress = self.current_step / self.total_steps
        
        if self.decay_type == "linear":
            temp = self.initial_temp - (self.initial_temp - self.final_temp) * progress
        elif self.decay_type == "exponential":
            temp = self.initial_temp * (self.decay_rate ** self.current_step)
            temp = max(temp, self.final_temp)
        elif self.decay_type == "cosine":
            import math
            temp = self.final_temp + (self.initial_temp - self.final_temp) * (
                0.5 * (1 + math.cos(math.pi * progress))
            )
        else:
            temp = self.initial_temp
        
        return max(self.final_temp, min(self.initial_temp, temp))
    
    def step(self):
        """Advance scheduler by one step."""
        self.current_step += 1
    
    def reset(self):
        """Reset scheduler to initial state."""
        self.current_step = 0
    
    def set_step(self, step: int):
        """
        Set current step manually.
        
        :param step: Step number to set
        """
        self.current_step = max(0, min(step, self.total_steps))

