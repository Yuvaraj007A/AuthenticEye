import torch
import torch.nn as nn

class VideoTemporalLSTM(nn.Module):
    """
    Takes a sequence of feature vectors (size 16) extracted from the per-frame fusion pipeline
    and processes them temporally to output a single logit for the video.
    """
    
    def __init__(self, input_dim=16, hidden_dim=64, num_layers=1, bidirectional=True):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim, 
            hidden_size=hidden_dim, 
            num_layers=num_layers,
            batch_first=True,
            bidirectional=bidirectional
        )
        
        lstm_out_dim = hidden_dim * 2 if bidirectional else hidden_dim
        
        self.classifier = nn.Sequential(
            nn.Linear(lstm_out_dim, 32),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(32, 1)
        )

    def forward(self, x):
        """
        x shape: (batch, seq_len, input_dim)
        """
        # lstm_out: (batch, seq_len, lstm_out_dim)
        lstm_out, _ = self.lstm(x)
        
        # Take the output of the last time step
        # Note: For bidirectional, this concatenates the last state of forward 
        # and the first state of backward, which is PyTorch's default behavior 
        # for last index.
        last_step_out = lstm_out[:, -1, :]
        
        logit = self.classifier(last_step_out)
        return logit
