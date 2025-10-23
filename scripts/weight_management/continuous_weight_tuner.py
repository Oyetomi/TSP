#!/usr/bin/env python3
"""
Continuous Weight Tuner
Keeps generating and testing new weight combinations until 90% accuracy is achieved
Uses genetic algorithm with mutation and crossover to evolve optimal weights
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import random
import math
from dataclasses import dataclass

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from weight_config_manager import config_manager

@dataclass
class Individual:
    """Individual in the genetic algorithm population"""
    weights: Dict[str, float]
    accuracy: float
    generation: int
    config_name: str

class ContinuousWeightTuner:
    """Continuously tunes weights using genetic algorithm until target is reached"""
    
    def __init__(self):
        self.target_accuracy = 0.90
        self.population_size = 20
        self.mutation_rate = 0.15
        self.crossover_rate = 0.7
        self.elite_size = 4
        self.max_generations = 500
        
        # Load historical matches for testing
        self.matches = self._load_historical_matches()
        print(f"📊 Loaded {len(self.matches)} historical matches for continuous tuning")
        
        # Weight factor names
        self.weight_factors = [
            'surface_performance',
            'set_performance', 
            'clutch_factor',
            'recent_form',
            'momentum',
            'physical_factors',
            'ranking_advantage'
        ]
        
        # Track best individuals across generations
        self.all_time_best = []
        self.generation_counter = 0
        
    def _load_historical_matches(self) -> List[Dict]:
        """Load historical matches from our cached data"""
        matches = []
        
        # Load from multiple sources
        files_to_try = [
            'data/simple_optimization_matches.json',
            'data/enhanced_optimization_matches.json',
            'data/real_optimization_matches.json'
        ]
        
        for filepath in files_to_try:
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        matches.extend(data)
                        if len(matches) >= 300:  # Enough data
                            break
                except:
                    continue
        
        return matches[:300]  # Limit for speed
    
    def generate_random_weights(self) -> Dict[str, float]:
        """Generate random normalized weights"""
        
        # Generate random values
        raw_weights = {}
        for factor in self.weight_factors:
            raw_weights[factor] = random.uniform(0.0, 1.0)
        
        # Normalize to sum to 1.0
        total = sum(raw_weights.values())
        if total > 0:
            for factor in raw_weights:
                raw_weights[factor] /= total
        
        return raw_weights
    
    def create_initial_population(self) -> List[Individual]:
        """Create initial population with diverse weight combinations"""
        
        population = []
        
        # Add some known good configurations
        known_configs = [
            {
                'surface_performance': 0.50, 'set_performance': 0.30, 'clutch_factor': 0.15,
                'recent_form': 0.05, 'momentum': 0.00, 'physical_factors': 0.00, 'ranking_advantage': 0.00
            },
            {
                'clutch_factor': 0.45, 'surface_performance': 0.25, 'set_performance': 0.20,
                'recent_form': 0.10, 'momentum': 0.00, 'physical_factors': 0.00, 'ranking_advantage': 0.00
            },
            {
                'set_performance': 0.60, 'surface_performance': 0.20, 'clutch_factor': 0.15,
                'recent_form': 0.05, 'momentum': 0.00, 'physical_factors': 0.00, 'ranking_advantage': 0.00
            }
        ]
        
        # Add known configs to population
        for i, weights in enumerate(known_configs):
            individual = Individual(
                weights=weights,
                accuracy=0.0,
                generation=0,
                config_name=f"SEED_{i+1}"
            )
            population.append(individual)
        
        # Fill rest with random individuals
        while len(population) < self.population_size:
            weights = self.generate_random_weights()
            individual = Individual(
                weights=weights,
                accuracy=0.0,
                generation=0,
                config_name=f"RANDOM_{len(population)}"
            )
            population.append(individual)
        
        return population
    
    def evaluate_individual(self, individual: Individual) -> float:
        """Evaluate an individual's fitness (accuracy on historical matches)"""
        
        correct_predictions = 0
        total_predictions = len(self.matches)
        
        for match in self.matches:
            # Quick prediction using weights
            predicted_plus_sets = self._predict_match(match, individual.weights)
            actual_plus_sets = match.get('good_for_plus_sets', match.get('total_sets', 0) >= 3)
            
            if predicted_plus_sets == actual_plus_sets:
                correct_predictions += 1
        
        accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0
        individual.accuracy = accuracy
        return accuracy
    
    def _predict_match(self, match: Dict, weights: Dict[str, float]) -> bool:
        """Quick prediction for a match using given weights"""
        
        # Surface factor
        surface = match.get('surface', 'Hard').lower()
        if 'clay' in surface:
            surface_factor = 0.7
        elif 'grass' in surface:
            surface_factor = 0.3
        else:
            surface_factor = 0.5
        
        # Tournament factor
        tournament = match.get('tournament', '').lower()
        if any(word in tournament for word in ['grand slam', 'masters', 'atp 500']):
            tournament_factor = 0.7
        elif 'atp 250' in tournament:
            tournament_factor = 0.5
        else:
            tournament_factor = 0.4
        
        # Player strength estimation (simplified)
        player1_strength = self._estimate_player_strength(match.get('player1_name', ''))
        player2_strength = self._estimate_player_strength(match.get('player2_name', ''))
        
        strength_diff = abs(player1_strength - player2_strength) / 100.0
        form_factor = 0.6 if strength_diff < 0.2 else 0.4  # Close matches more likely to go longer
        
        # Calculate weighted prediction
        prediction_score = 0.0
        prediction_score += weights.get('surface_performance', 0) * surface_factor
        prediction_score += weights.get('set_performance', 0) * tournament_factor
        prediction_score += weights.get('clutch_factor', 0) * (0.7 if strength_diff < 0.15 else 0.5)
        prediction_score += weights.get('recent_form', 0) * form_factor
        prediction_score += weights.get('momentum', 0) * (0.6 if 'clay' in surface else 0.4)
        prediction_score += weights.get('physical_factors', 0) * tournament_factor
        prediction_score += weights.get('ranking_advantage', 0) * (0.5 - strength_diff)
        
        # Enhanced factors for better prediction
        if 'clay' in surface:
            prediction_score += 0.1
        if any(word in tournament for word in ['masters', 'grand slam']):
            prediction_score += 0.05
        
        # Convert to probability and make prediction
        plus_sets_probability = max(0.2, min(0.8, prediction_score))
        return plus_sets_probability > 0.5
    
    def _estimate_player_strength(self, player_name: str) -> float:
        """Estimate player strength (simplified)"""
        if not player_name:
            return 50.0
        
        # Use hash for consistent but varied strengths
        name_hash = hash(player_name) % 40
        return 45.0 + name_hash
    
    def mutate_individual(self, individual: Individual) -> Individual:
        """Mutate an individual's weights"""
        
        new_weights = individual.weights.copy()
        
        # Mutate each weight with some probability
        for factor in self.weight_factors:
            if random.random() < self.mutation_rate:
                # Add random noise
                mutation_strength = random.uniform(-0.1, 0.1)
                new_weights[factor] = max(0.0, new_weights[factor] + mutation_strength)
        
        # Renormalize weights
        total = sum(new_weights.values())
        if total > 0:
            for factor in new_weights:
                new_weights[factor] /= total
        
        return Individual(
            weights=new_weights,
            accuracy=0.0,
            generation=self.generation_counter + 1,
            config_name=f"MUTANT_{self.generation_counter}_{random.randint(1000, 9999)}"
        )
    
    def crossover_individuals(self, parent1: Individual, parent2: Individual) -> Individual:
        """Create offspring by crossing over two parents"""
        
        new_weights = {}
        
        # Blend weights from both parents
        for factor in self.weight_factors:
            # Random blend between parents
            blend_ratio = random.uniform(0.3, 0.7)
            new_weights[factor] = (
                blend_ratio * parent1.weights[factor] +
                (1 - blend_ratio) * parent2.weights[factor]
            )
        
        # Renormalize
        total = sum(new_weights.values())
        if total > 0:
            for factor in new_weights:
                new_weights[factor] /= total
        
        return Individual(
            weights=new_weights,
            accuracy=0.0,
            generation=self.generation_counter + 1,
            config_name=f"CROSS_{self.generation_counter}_{random.randint(1000, 9999)}"
        )
    
    def evolve_population(self, population: List[Individual]) -> List[Individual]:
        """Evolve population to next generation"""
        
        # Sort by fitness (accuracy)
        population.sort(key=lambda x: x.accuracy, reverse=True)
        
        # Keep elite individuals
        new_population = population[:self.elite_size].copy()
        
        # Generate rest of population through crossover and mutation
        while len(new_population) < self.population_size:
            if random.random() < self.crossover_rate and len(population) >= 2:
                # Select parents (bias toward better individuals)
                parent1 = self._tournament_selection(population)
                parent2 = self._tournament_selection(population)
                offspring = self.crossover_individuals(parent1, parent2)
            else:
                # Mutate existing individual
                parent = self._tournament_selection(population)
                offspring = self.mutate_individual(parent)
            
            new_population.append(offspring)
        
        return new_population
    
    def _tournament_selection(self, population: List[Individual], tournament_size: int = 3) -> Individual:
        """Select individual using tournament selection"""
        
        tournament = random.sample(population, min(tournament_size, len(population)))
        return max(tournament, key=lambda x: x.accuracy)
    
    def run_continuous_optimization(self):
        """Run continuous optimization until target accuracy is reached"""
        
        print("🚀 CONTINUOUS WEIGHT TUNING")
        print("🧬 Genetic Algorithm Evolution")
        print("🎯 Target: 90% Accuracy")
        print("🔄 Will keep trying until target is reached!")
        print("=" * 60)
        
        # Create initial population
        population = self.create_initial_population()
        
        # Evaluate initial population
        print(f"🧪 Evaluating initial population of {len(population)} individuals...")
        for individual in population:
            self.evaluate_individual(individual)
        
        # Track best individual ever
        best_ever = max(population, key=lambda x: x.accuracy)
        self.all_time_best.append(best_ever)
        
        print(f"🏆 Initial best: {best_ever.accuracy:.1%} ({best_ever.config_name})")
        
        # Evolution loop
        generations_without_improvement = 0
        max_stagnation = 50
        
        for generation in range(self.max_generations):
            self.generation_counter = generation
            
            # Evolve population
            population = self.evolve_population(population)
            
            # Evaluate new individuals
            for individual in population:
                if individual.accuracy == 0.0:  # Only evaluate new individuals
                    self.evaluate_individual(individual)
            
            # Find best in this generation
            generation_best = max(population, key=lambda x: x.accuracy)
            
            # Check if we found a new all-time best
            if generation_best.accuracy > best_ever.accuracy:
                best_ever = generation_best
                self.all_time_best.append(best_ever)
                generations_without_improvement = 0
                
                print(f"🎉 Gen {generation:3d}: NEW BEST! {best_ever.accuracy:.1%} ({best_ever.config_name})")
                
                # Show the weights of this new best
                print(f"    📊 Weights:")
                sorted_weights = sorted(best_ever.weights.items(), key=lambda x: x[1], reverse=True)
                for factor, weight in sorted_weights:
                    if weight > 0.01:  # Only show significant weights
                        print(f"        {factor:<20}: {weight:>6.1%}")
                
                # Check if we hit target
                if best_ever.accuracy >= self.target_accuracy:
                    print(f"🎯 TARGET ACHIEVED! {best_ever.accuracy:.1%} >= {self.target_accuracy:.1%}")
                    break
            else:
                generations_without_improvement += 1
                
                # Show progress every 10 generations
                if generation % 10 == 0:
                    avg_accuracy = sum(ind.accuracy for ind in population) / len(population)
                    print(f"📊 Gen {generation:3d}: Best {best_ever.accuracy:.1%}, Avg {avg_accuracy:.1%}, Stagnant {generations_without_improvement}")
            
            # Check for stagnation
            if generations_without_improvement >= max_stagnation:
                print(f"⚠️ No improvement for {max_stagnation} generations. Introducing fresh blood...")
                
                # Replace worst half with new random individuals
                population.sort(key=lambda x: x.accuracy, reverse=True)
                num_to_replace = len(population) // 2
                
                for i in range(num_to_replace):
                    population[-(i+1)] = Individual(
                        weights=self.generate_random_weights(),
                        accuracy=0.0,
                        generation=generation,
                        config_name=f"FRESH_{generation}_{i}"
                    )
                
                generations_without_improvement = 0
        
        # Final results
        print(f"\n🏆 CONTINUOUS OPTIMIZATION RESULTS:")
        print("=" * 60)
        print(f"Best accuracy achieved: {best_ever.accuracy:.1%}")
        print(f"Generations run: {generation + 1}")
        print(f"Target achieved: {'🎉 YES!' if best_ever.accuracy >= self.target_accuracy else '❌ No'}")
        
        # Show final optimal weights
        print(f"\n📊 OPTIMAL WEIGHTS:")
        sorted_weights = sorted(best_ever.weights.items(), key=lambda x: x[1], reverse=True)
        for factor, weight in sorted_weights:
            print(f"   {factor:<20}: {weight:>6.1%}")
        
        # Save best configuration
        if best_ever.accuracy >= 0.60:  # Save if reasonably good
            final_config_name = "CONTINUOUS_OPTIMIZED_V1"
            try:
                config_manager.add_config(
                    final_config_name,
                    "Continuous Optimization V1",
                    f"Evolved through {generation + 1} generations, {best_ever.accuracy:.1%} accuracy",
                    best_ever.weights
                )
                
                print(f"\n🎯 SAVED BEST CONFIGURATION: {final_config_name}")
                print(f"   To activate: python3 manage_weights.py set {final_config_name}")
                
            except Exception as e:
                print(f"   ⚠️ Could not save config: {e}")
        
        # Save evolution history
        evolution_data = {
            'optimization_date': datetime.now().isoformat(),
            'method': 'continuous_genetic_algorithm',
            'target_accuracy': self.target_accuracy,
            'generations_run': generation + 1,
            'best_accuracy': best_ever.accuracy,
            'target_achieved': best_ever.accuracy >= self.target_accuracy,
            'evolution_history': [
                {
                    'generation': best.generation,
                    'accuracy': best.accuracy,
                    'config_name': best.config_name,
                    'weights': best.weights
                }
                for best in self.all_time_best
            ]
        }
        
        with open('data/continuous_optimization_results.json', 'w') as f:
            json.dump(evolution_data, f, indent=2)
        
        return best_ever

def main():
    """Run continuous weight optimization"""
    
    print("🎾 CONTINUOUS TENNIS WEIGHT OPTIMIZER")
    print("🧬 Evolving Weights Until 90% Accuracy")
    print("🔄 Never Gives Up!")
    print("📅 August 21st, 2025")
    print("=" * 60)
    
    tuner = ContinuousWeightTuner()
    best_result = tuner.run_continuous_optimization()
    
    if best_result.accuracy >= tuner.target_accuracy:
        print(f"\n🎉 MISSION ACCOMPLISHED!")
        print(f"💡 Achieved {best_result.accuracy:.1%} accuracy!")
        print(f"🚀 Model is ready for production!")
    else:
        print(f"\n📈 Best result: {best_result.accuracy:.1%}")
        print(f"💡 Continue evolution or adjust strategy!")

if __name__ == "__main__":
    main()
